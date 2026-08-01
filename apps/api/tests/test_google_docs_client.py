import pytest

from apps.api.app.integrations.google_docs_client import (
    GoogleDocsClient,
    parse_google_doc_url,
)


def test_folder_listing_is_paginated_and_filters_non_docs() -> None:
    drive = FakeDriveService()
    client = GoogleDocsClient(drive_service=drive, docs_service=object())

    documents = client.list_folder_docs("folder_123")

    assert [item["id"] for item in documents] == ["doc-1", "doc-2"]
    assert drive.page_tokens == [None, "next"]


def test_google_document_url_parser_accepts_share_links_and_rejects_other_hosts() -> None:
    assert (
        parse_google_doc_url(
            "https://docs.google.com/document/d/demo-document-id/edit?tab=t.0"
        )
        == "demo-document-id"
    )
    with pytest.raises(ValueError):
        parse_google_doc_url("https://example.com/document/d/demo-document-id/edit")


class FakeDriveService:
    def __init__(self):
        self.page_tokens: list[str | None] = []
        self.current_token: str | None = None

    def files(self):
        return self

    def list(self, **kwargs: object):
        self.current_token = kwargs["pageToken"]
        self.page_tokens.append(self.current_token)
        return self

    def execute(self):
        if self.current_token is None:
            return {
                "nextPageToken": "next",
                "files": [
                    {"id": "doc-1", "mimeType": "application/vnd.google-apps.document"},
                    {"id": "pdf-1", "mimeType": "application/pdf"},
                ],
            }
        return {
            "files": [
                {"id": "doc-2", "mimeType": "application/vnd.google-apps.document"}
            ]
        }
