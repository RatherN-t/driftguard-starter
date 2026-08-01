import pytest

from apps.api.app.integrations.github_client import parse_pr_url, parse_repository_url


def test_parse_canonical_pr_url() -> None:
    parsed = parse_pr_url("https://github.com/acme/payments/pull/42")

    assert (parsed.owner, parsed.repo, parsed.number) == ("acme", "payments", 42)
    assert parsed.canonical_url == "https://github.com/acme/payments/pull/42"
    assert parsed.source_id == "github:acme/payments:pull/42"


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/acme/payments/pull/42",
        "https://example.com/acme/payments/pull/42",
        "https://api.github.com/acme/payments/pull/42",
        "https://github.com:443/acme/payments/pull/42",
        "https://github.com/acme/payments/pull/42?diff=split",
        "https://github.com/acme/payments/pull/42#discussion",
        "https://github.com/acme/payments/pulls/42",
        "https://github.com/acme/payments/pull/0",
        "https://github.com/acme/payments/pull/042",
        "https://github.com/acme/payments/pull/not-a-number",
        "https://github.com/acme/payments/pull/42/files",
        "https://user@github.com/acme/payments/pull/42",
    ],
)
def test_reject_noncanonical_pr_url(url: str) -> None:
    with pytest.raises(ValueError):
        parse_pr_url(url)


def test_parse_repository_url_is_canonical_and_traceable() -> None:
    parsed = parse_repository_url("https://github.com/example/driftguard-demo")

    assert parsed.owner == "example"
    assert parsed.repo == "driftguard-demo"
    assert parsed.canonical_url == "https://github.com/example/driftguard-demo"


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/example/repo",
        "https://github.com/example/repo/issues",
        "https://gitlab.com/example/repo",
        "https://github.com/example/repo?tab=readme",
    ],
)
def test_parse_repository_url_rejects_noncanonical_urls(url: str) -> None:
    with pytest.raises(ValueError):
        parse_repository_url(url)
