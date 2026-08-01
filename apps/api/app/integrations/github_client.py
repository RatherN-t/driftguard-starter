import re
from dataclasses import dataclass
from typing import Self
from urllib.parse import quote, urlsplit

import httpx

_OWNER = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+$")
_NEXT_LINK = re.compile(r"<[^>]+>;\s*rel=\"next\"")


class GitHubClientError(RuntimeError):
    """Base class for sanitized, user-safe GitHub read errors."""


class GitHubAuthenticationError(GitHubClientError):
    pass


class GitHubTimeoutError(GitHubClientError):
    pass


class GitHubAPIError(GitHubClientError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"GitHub read failed with HTTP {status_code}")


class GitHubLimitError(GitHubClientError):
    pass


@dataclass(frozen=True)
class ParsedPR:
    owner: str
    repo: str
    number: int

    @property
    def source_id(self) -> str:
        return f"github:{self.owner}/{self.repo}:pull/{self.number}"

    @property
    def canonical_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}/pull/{self.number}"

    @property
    def repository_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}"


@dataclass(frozen=True)
class ParsedRepository:
    owner: str
    repo: str

    @property
    def canonical_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}"


def parse_pr_url(url: str) -> ParsedPR:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Expected canonical https://github.com/{owner}/{repo}/pull/{number}")

    path = parsed.path.removesuffix("/")
    parts = path.split("/")
    if len(parts) != 5 or parts[0] or parts[3] != "pull":
        raise ValueError("Expected canonical https://github.com/{owner}/{repo}/pull/{number}")

    owner, repo, number_text = parts[1], parts[2], parts[4]
    if not _OWNER.fullmatch(owner) or not _REPOSITORY.fullmatch(repo):
        raise ValueError("GitHub owner or repository is invalid")
    if not number_text.isascii() or not number_text.isdigit() or number_text.startswith("0"):
        raise ValueError("GitHub pull request number must be a positive canonical integer")
    number = int(number_text)
    if number < 1:
        raise ValueError("GitHub pull request number must be positive")
    return ParsedPR(owner=owner, repo=repo, number=number)


def parse_repository_url(url: str) -> ParsedRepository:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Expected canonical https://github.com/{owner}/{repo}")
    path = parsed.path.removesuffix("/")
    parts = path.split("/")
    if len(parts) != 3 or parts[0]:
        raise ValueError("Expected canonical https://github.com/{owner}/{repo}")
    owner, repo = parts[1], parts[2]
    if not _OWNER.fullmatch(owner) or not _REPOSITORY.fullmatch(repo):
        raise ValueError("GitHub owner or repository is invalid")
    return ParsedRepository(owner=owner, repo=repo)


class GitHubClient:
    def __init__(
        self,
        token: str | None = None,
        *,
        max_changed_files: int = 10,
        max_file_bytes: int = 100_000,
        timeout_seconds: float = 20,
        client: httpx.Client | None = None,
    ):
        if max_changed_files < 1 or max_file_bytes < 1:
            raise ValueError("GitHub limits must be positive")
        self.max_changed_files = max_changed_files
        self.max_file_bytes = max_file_bytes
        self._owns_client = client is None
        self.client = client or httpx.Client(
            base_url="https://api.github.com", timeout=timeout_seconds
        )
        self.client.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "DriftGuard/0.1",
            }
        )
        if token:
            self.client.headers["Authorization"] = f"Bearer {token}"

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def get_pr(self, parsed: ParsedPR) -> dict:
        response = self._request(
            "GET", f"/repos/{parsed.owner}/{parsed.repo}/pulls/{parsed.number}"
        )
        payload = response.json()
        if not isinstance(payload, dict):
            raise GitHubClientError("GitHub returned invalid pull request metadata")
        return payload

    def list_files(self, parsed: ParsedPR) -> list[dict]:
        files: list[dict] = []
        page = 1
        while True:
            response = self._request(
                "GET",
                f"/repos/{parsed.owner}/{parsed.repo}/pulls/{parsed.number}/files",
                params={"per_page": 100, "page": page},
            )
            payload = response.json()
            if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
                raise GitHubClientError("GitHub returned invalid changed-file metadata")
            if len(files) + len(payload) > self.max_changed_files:
                raise GitHubLimitError(
                    f"Pull request exceeds the configured {self.max_changed_files}-file limit"
                )
            files.extend(payload)
            if not _NEXT_LINK.search(response.headers.get("Link", "")):
                break
            page += 1
            if page > self.max_changed_files + 1:
                raise GitHubClientError("GitHub pagination exceeded the safe page limit")
        return files

    def get_full_file(self, parsed: ParsedPR, *, path: str, ref: str) -> str:
        if not path or path.startswith(("/", "\\")) or ".." in path.replace("\\", "/").split("/"):
            raise ValueError("GitHub file path must be repository-relative")
        if not ref:
            raise ValueError("GitHub file ref must not be empty")
        response = self._request(
            "GET",
            f"/repos/{parsed.owner}/{parsed.repo}/contents/{quote(path, safe='/')}",
            params={"ref": ref},
            headers={"Accept": "application/vnd.github.raw+json"},
        )
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > self.max_file_bytes:
            raise GitHubLimitError(
                f"GitHub file exceeds the configured {self.max_file_bytes}-byte limit"
            )
        if len(response.content) > self.max_file_bytes:
            raise GitHubLimitError(
                f"GitHub file exceeds the configured {self.max_file_bytes}-byte limit"
            )
        return response.content.decode("utf-8", errors="replace")

    def fetch_pr(self, parsed: ParsedPR, *, include_full_files: bool = False) -> dict:
        metadata = self.get_pr(parsed)
        changed_files = metadata.get("changed_files")
        if isinstance(changed_files, int) and changed_files > self.max_changed_files:
            raise GitHubLimitError(
                f"Pull request exceeds the configured {self.max_changed_files}-file limit"
            )
        files = self.list_files(parsed)
        result: dict = {"pr": metadata, "files": files, "full_files": {}}
        if include_full_files:
            ref = _selected_sha(metadata)
            result["full_files"] = {
                item["filename"]: self.get_full_file(parsed, path=item["filename"], ref=ref)
                for item in files
                if isinstance(item.get("filename"), str)
            }
        return result

    def _request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        try:
            response = self.client.request(method, url, **kwargs)
        except httpx.TimeoutException as exc:
            raise GitHubTimeoutError("GitHub read timed out") from exc
        except httpx.RequestError as exc:
            raise GitHubClientError("GitHub read failed before receiving a response") from exc
        if response.status_code in {401, 403}:
            raise GitHubAuthenticationError("GitHub authentication or access was rejected")
        if response.status_code >= 400:
            raise GitHubAPIError(response.status_code)
        return response


def _selected_sha(metadata: dict) -> str:
    merge_sha = metadata.get("merge_commit_sha")
    if isinstance(merge_sha, str) and merge_sha:
        return merge_sha
    head = metadata.get("head")
    if isinstance(head, dict) and isinstance(head.get("sha"), str) and head["sha"]:
        return head["sha"]
    raise GitHubClientError("GitHub pull request has no usable merge or head SHA")
