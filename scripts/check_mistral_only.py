import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN = [ROOT / "pyproject.toml", ROOT / "apps", ROOT / "scripts"]
BANNED = ["openai", "anthropic", "gemini", "google.generativeai", "cohere"]
ALLOW_FILES = {Path(__file__).resolve()}
IGNORED_DIRECTORIES = {
    ".bootstrap",
    ".next",
    ".python",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}


def main() -> None:
    hits: list[str] = []
    files: list[Path] = []
    for item in SCAN:
        files.extend([item] if item.is_file() else item.rglob("*"))
    for path in files:
        relative_parts = path.relative_to(ROOT).parts
        if any(part in IGNORED_DIRECTORIES for part in relative_parts):
            continue
        if (
            not path.is_file()
            or path in ALLOW_FILES
            or path.suffix not in {".py", ".toml", ".json", ".ts", ".tsx"}
        ):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for token in BANNED:
            if token in text:
                hits.append(f"{path.relative_to(ROOT)}: {token}")
    if hits:
        print("Non-Mistral provider references found in executable source/dependencies:")
        print("\n".join(hits))
        sys.exit(1)
    print("Mistral-only provider check passed")


if __name__ == "__main__":
    main()
