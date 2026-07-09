from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"


def load_doc(name: str) -> str:
    """Read a markdown doc shipped under dagster_project/docs/ by filename."""
    return (DOCS_DIR / name).read_text()
