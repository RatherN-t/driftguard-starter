import re
from pathlib import Path
from urllib.parse import urlsplit

from google.oauth2 import service_account
from googleapiclient.discovery import build

from apps.api.app.domain.schemas import DocumentPatchProposal

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents",
]
_FOLDER_ID = re.compile(r"^[A-Za-z0-9_-]+$")
_DOCUMENT_ID = re.compile(r"^[A-Za-z0-9_-]+$")


class DocumentRevisionConflict(RuntimeError):
    pass


class DocumentTargetConflict(RuntimeError):
    pass


def document_body(document: dict) -> dict:
    """Return the only document body from legacy or tab-aware Docs responses."""
    legacy_body = document.get("body")
    if isinstance(legacy_body, dict):
        return legacy_body

    bodies: list[dict] = []

    def collect(tabs: object) -> None:
        if not isinstance(tabs, list):
            return
        for tab in tabs:
            if not isinstance(tab, dict):
                continue
            document_tab = tab.get("documentTab")
            if isinstance(document_tab, dict) and isinstance(document_tab.get("body"), dict):
                bodies.append(document_tab["body"])
            collect(tab.get("childTabs"))

    collect(document.get("tabs"))
    if not bodies:
        raise ValueError("Google document has no readable body")
    if len(bodies) > 1:
        raise ValueError("Google Docs MVP supports documents with one tab")
    return bodies[0]


def parse_google_doc_url(url: str) -> str:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "docs.google.com"
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("Expected a Google Docs URL")
    parts = parsed.path.rstrip("/").split("/")
    if len(parts) < 4 or parts[:3] != ["", "document", "d"]:
        raise ValueError("Expected https://docs.google.com/document/d/{document_id}")
    document_id = parts[3]
    if not _DOCUMENT_ID.fullmatch(document_id):
        raise ValueError("Google document ID is invalid")
    return document_id


class GoogleDocsClient:
    def __init__(
        self,
        credential_file: str | None = None,
        *,
        drive_service: object | None = None,
        docs_service: object | None = None,
    ):
        if drive_service is not None and docs_service is not None:
            self.drive = drive_service
            self.docs = docs_service
            return
        if not credential_file:
            raise ValueError("Google credential file is required")
        path = Path(credential_file)
        if not path.is_file():
            raise FileNotFoundError("Configured Google credential file was not found")
        credentials = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
        self.drive = build("drive", "v3", credentials=credentials, cache_discovery=False)
        self.docs = build("docs", "v1", credentials=credentials, cache_discovery=False)

    def list_folder_docs(self, folder_id: str) -> list[dict]:
        if not _FOLDER_ID.fullmatch(folder_id):
            raise ValueError("Google Drive folder ID is invalid")
        query = f"'{folder_id}' in parents and trashed=false"
        documents: list[dict] = []
        page_token: str | None = None
        while True:
            result = (
                self.drive.files()
                .list(
                    q=query,
                    fields="nextPageToken,files(id,name,mimeType,modifiedTime,version,webViewLink)",
                    pageToken=page_token,
                )
                .execute()
            )
            documents.extend(
                item
                for item in result.get("files", [])
                if item["mimeType"] == "application/vnd.google-apps.document"
            )
            page_token = result.get("nextPageToken")
            if not page_token:
                break
        return documents

    def get_document(self, document_id: str) -> dict:
        return (
            self.docs.documents()
            .get(documentId=document_id, includeTabsContent=True)
            .execute()
        )

    def batch_update(
        self, document_id: str, requests: list[dict], required_revision_id: str
    ) -> dict:
        body = {
            "requests": requests,
            "writeControl": {"requiredRevisionId": required_revision_id},
        }
        return self.docs.documents().batchUpdate(documentId=document_id, body=body).execute()

    def apply_patch(self, document_id: str, proposal: DocumentPatchProposal) -> dict:
        document = self.get_document(document_id)
        actual_revision = document.get("revisionId")
        if actual_revision != proposal.expected_revision:
            raise DocumentRevisionConflict("Google document revision changed before apply")

        prepared: list[tuple[int, int, str]] = []
        for operation in proposal.operations:
            if operation.operation != "replace_range" or not operation.original_text:
                raise ValueError("Live Google Docs MVP supports replace_range operations only")
            start, end = _character_range(operation.locator)
            actual_text = _document_text_range(document, start, end)
            if actual_text != operation.original_text:
                raise DocumentTargetConflict("Google document target text changed before apply")
            prepared.append((start, end, operation.replacement_text))

        requests: list[dict] = []
        for start, end, replacement in sorted(prepared, reverse=True):
            requests.extend(
                [
                    {"deleteContentRange": {"range": {"startIndex": start, "endIndex": end}}},
                    {"insertText": {"location": {"index": start}, "text": replacement}},
                ]
            )
        return self.batch_update(document_id, requests, proposal.expected_revision)


def _character_range(locator: str) -> tuple[int, int]:
    if not locator.startswith("chars:") or "-" not in locator:
        raise ValueError("Google Docs patch locator must use chars:start-end")
    start_text, end_text = locator.removeprefix("chars:").split("-", 1)
    start, end = int(start_text), int(end_text)
    if start < 1 or end <= start:
        raise ValueError("Google Docs character range is invalid")
    return start, end


def _document_text_range(document: dict, start: int, end: int) -> str:
    chunks: list[str] = []
    for structural in document_body(document).get("content", []):
        paragraph = structural.get("paragraph")
        if not isinstance(paragraph, dict):
            continue
        for element in paragraph.get("elements", []):
            text_run = element.get("textRun")
            if not isinstance(text_run, dict):
                continue
            element_start = int(element.get("startIndex", 0))
            element_end = int(element.get("endIndex", element_start))
            overlap_start = max(start, element_start)
            overlap_end = min(end, element_end)
            if overlap_start < overlap_end:
                content = str(text_run.get("content", ""))
                chunks.append(
                    content[overlap_start - element_start : overlap_end - element_start]
                )
    return "".join(chunks)
