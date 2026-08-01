import httpx
import pytest

from apps.api.app.integrations.github_client import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubClient,
    GitHubLimitError,
    GitHubTimeoutError,
    parse_pr_url,
)

PARSED = parse_pr_url("https://github.com/acme/payments/pull/42")


def test_fetch_pr_success_sends_read_headers_without_exposing_token() -> None:
    seen_authorization = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_authorization
        seen_authorization = request.headers.get("Authorization") == "Bearer test-secret"
        if request.url.path.endswith("/files"):
            return httpx.Response(200, json=[{"filename": "payment.py"}])
        return httpx.Response(200, json={"number": 42, "changed_files": 1})

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="https://api.github.com")
    client = GitHubClient(token="test-secret", client=http_client)

    result = client.fetch_pr(PARSED)

    assert result["pr"]["number"] == 42
    assert result["files"] == [{"filename": "payment.py"}]
    assert seen_authorization is True


def test_fetch_pr_can_load_full_files_at_merge_sha() -> None:
    requested_ref = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requested_ref
        if "/contents/" in request.url.path:
            requested_ref = request.url.params["ref"]
            return httpx.Response(200, content=b"print('payment')\n")
        if request.url.path.endswith("/files"):
            return httpx.Response(200, json=[{"filename": "src/payment.py"}])
        return httpx.Response(
            200,
            json={"number": 42, "changed_files": 1, "merge_commit_sha": "merge123"},
        )

    client = _client(handler)

    result = client.fetch_pr(PARSED, include_full_files=True)

    assert requested_ref == "merge123"
    assert result["full_files"] == {"src/payment.py": "print('payment')\n"}


def test_list_files_follows_pagination() -> None:
    requested_pages: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_pages.append(request.url.params["page"])
        if request.url.params["page"] == "1":
            return httpx.Response(
                200,
                json=[{"filename": "one.py"}],
                headers={"Link": '<https://api.github.com/next>; rel="next"'},
            )
        return httpx.Response(200, json=[{"filename": "two.py"}])

    client = _client(handler, max_changed_files=2)

    files = client.list_files(PARSED)

    assert requested_pages == ["1", "2"]
    assert [item["filename"] for item in files] == ["one.py", "two.py"]


def test_authentication_error_is_sanitized() -> None:
    client = _client(lambda _: httpx.Response(401, text="sensitive upstream body"))

    with pytest.raises(GitHubAuthenticationError) as error:
        client.get_pr(PARSED)

    assert "sensitive" not in str(error.value)


def test_timeout_is_translated() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client = _client(handler)

    with pytest.raises(GitHubTimeoutError):
        client.get_pr(PARSED)


def test_api_error_is_sanitized() -> None:
    client = _client(lambda _: httpx.Response(500, json={"message": "internal detail"}))

    with pytest.raises(GitHubAPIError) as error:
        client.get_pr(PARSED)

    assert error.value.status_code == 500
    assert "internal detail" not in str(error.value)


def test_metadata_file_limit_is_enforced_before_listing() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"number": 42, "changed_files": 3})

    client = _client(handler, max_changed_files=2)

    with pytest.raises(GitHubLimitError):
        client.fetch_pr(PARSED)

    assert calls == 1


def test_paginated_file_limit_is_enforced() -> None:
    client = _client(
        lambda _: httpx.Response(
            200,
            json=[{"filename": "one.py"}, {"filename": "two.py"}],
        ),
        max_changed_files=1,
    )

    with pytest.raises(GitHubLimitError):
        client.list_files(PARSED)


def test_full_file_byte_limit_checks_body_and_path() -> None:
    client = _client(lambda _: httpx.Response(200, content=b"12345"), max_file_bytes=4)

    with pytest.raises(GitHubLimitError):
        client.get_full_file(PARSED, path="src/payment.py", ref="abc123")
    with pytest.raises(ValueError):
        client.get_full_file(PARSED, path="../secret", ref="abc123")


def test_demo_api_uses_labelled_fixture_without_network() -> None:
    from fastapi.testclient import TestClient

    from apps.api.app.main import app

    response = TestClient(app).post(
        "/api/sources/github/pr",
        json={"url": "https://github.com/example/driftguard-demo/pull/7"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provenance"]["mode"] == "demo_fixture"
    assert payload["provenance"]["is_demo"] is True
    assert payload["pr"]["number"] == 7
    assert sorted(payload["full_files"]) == ["payment_api.py", "payment_worker.py"]
    assert payload["evidence"]


def _client(
    handler: httpx.MockTransport | object,
    *,
    max_changed_files: int = 10,
    max_file_bytes: int = 100_000,
) -> GitHubClient:
    transport = handler if isinstance(handler, httpx.MockTransport) else httpx.MockTransport(handler)
    return GitHubClient(
        client=httpx.Client(transport=transport, base_url="https://api.github.com"),
        max_changed_files=max_changed_files,
        max_file_bytes=max_file_bytes,
    )
