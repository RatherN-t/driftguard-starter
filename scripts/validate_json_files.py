import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRECTORIES = {
    ".bootstrap",
    ".next",
    ".python",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}


def is_project_file(path: Path) -> bool:
    return not any(part in IGNORED_DIRECTORIES for part in path.relative_to(ROOT).parts)


def main() -> None:
    count = 0
    for path in ROOT.rglob("*.json"):
        if not is_project_file(path):
            continue
        json.loads(path.read_text(encoding="utf-8"))
        count += 1
    for path in ROOT.rglob("*.jsonl"):
        if not is_project_file(path):
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                json.loads(line)
        count += 1
    print(f"Validated {count} JSON/JSONL files")


if __name__ == "__main__":
    main()
