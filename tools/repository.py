"""Limit model-visible files and edits to the workshop's application surface."""

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
APP_FILES = (
    "app.py", "static/app.js", "static/style.css", "templates/index.html",
)
FEATURE_TEST = "tests/test_priority.py"
WRITABLE = (*APP_FILES, FEATURE_TEST)
READABLE = (*WRITABLE, "tests/test_app.py")
MAX_BYTES = 100_000


def safe_path(name: str, allowed=READABLE) -> Path:
    """Reject unknown paths and symlinks before reading or writing files."""
    if not isinstance(name, str) or name not in allowed:
        raise ValueError(f"File is outside the workshop allowlist: {name!r}")
    path = ROOT / name
    if any(part.is_symlink() for part in (path, *path.parents)
           if part != ROOT.parent):
        raise ValueError(f"Symlink paths are not allowed: {name}")
    if not path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Path leaves the repository")
    return path


def get_files(file_paths: list[str]) -> str:
    """Read bounded application context, including a missing feature-test file."""
    contents = []
    for name in file_paths:
        path = safe_path(name)
        if path.exists() and path.stat().st_size > MAX_BYTES:
            raise ValueError(f"File is too large: {name}")
        content = path.read_text() if path.exists() else "(File does not exist)"
        contents.append(f"--- FILE: {name} ---\n{content}\n")
    return "\n".join(contents)


def apply_edits(edits: list[dict]) -> str:
    """Validate the entire edit batch before replacing any allowed file."""
    if not isinstance(edits, list) or not edits:
        raise ValueError("Expected a non-empty edits list")
    validated = []
    seen = set()
    for edit in edits:
        if not isinstance(edit, dict):
            raise ValueError("Each edit must be an object")
        name, content = edit.get("file_path"), edit.get("content")
        path = safe_path(name, WRITABLE)
        if name in seen or not isinstance(content, str):
            raise ValueError("Duplicate path or non-string file content")
        if len(content.encode()) > MAX_BYTES:
            raise ValueError(f"Edit is too large: {name}")
        seen.add(name)
        validated.append((path, content))
    for path, content in validated:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return f"Successfully applied {len(validated)} edits."


def git(*args: str) -> str:
    """Run a checked Git operation in this checkout, never the caller's cwd."""
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True,
        timeout=30, check=True,
    )
    return result.stdout


def get_repository_diff() -> str:
    """Include staged, unstaged, and new allowed files in reviewer context."""
    diff = git("diff", "HEAD", "--", *WRITABLE)
    untracked = git("ls-files", "--others", "--exclude-standard", "--",
                    *WRITABLE).splitlines()
    for name in untracked:
        path = safe_path(name, WRITABLE)
        diff += f"\n--- NEW FILE: {name} ---\n{path.read_text()}\n"
    if len(diff.encode()) > MAX_BYTES * len(WRITABLE):
        raise ValueError("Diff is too large for this workshop")
    return diff
