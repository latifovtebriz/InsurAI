"""Pre-push secret scanner and repository hygiene checker."""

import re
import subprocess
import sys
from pathlib import Path

FORBIDDEN_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"AIzaSy[A-Za-z0-9_-]{33}"),  # Google API key pattern
    re.compile(r"sk-[a-zA-Z0-9]{20,T}"),  # Generic / OpenAI secret pattern
    re.compile(
        r"postgres(ql)?://[^:\s]+:[^@\s]+@"
    ),  # DB URI with real password (except change_me or placeholders)
]

FORBIDDEN_FILE_EXTENSIONS = [".pem", ".key", ".p12", ".pfx", ".kdbx", ".dump", ".sql.gz"]

IGNORED_PATHS = {".git", ".venv", "venv", "__pycache__", "node_modules"}


def check_git_tracked_files() -> list[str]:
    """Runs git ls-files and ensures no secret files or real env files are tracked."""
    violations: list[str] = []
    try:
        output = subprocess.check_output(["git", "ls-files"], text=True, encoding="utf-8")
        tracked_files = output.strip().splitlines()
    except Exception as exc:
        print(f"Error running git ls-files: {exc}")
        return ["Failed to inspect git tracked files"]

    for f in tracked_files:
        f_lower = f.lower()
        if f_lower == ".env" or f_lower.endswith("/.env"):
            violations.append(f"Tracked .env file detected: {f}")
        for ext in FORBIDDEN_FILE_EXTENSIONS:
            if f_lower.endswith(ext):
                violations.append(f"Forbidden extension tracked: {f}")

    return violations


def scan_file_contents(repo_root: Path) -> list[str]:
    """Scans tracked files for high-entropy secret patterns."""
    violations: list[str] = []
    try:
        output = subprocess.check_output(["git", "ls-files"], text=True, encoding="utf-8")
        tracked_files = [repo_root / f for f in output.strip().splitlines()]
    except Exception:
        tracked_files = list(repo_root.rglob("*"))

    for file_path in tracked_files:
        if not file_path.is_file():
            continue
        if any(part in file_path.parts for part in IGNORED_PATHS):
            continue
        if file_path.suffix in [".png", ".jpg", ".jpeg", ".ico", ".pdf"]:
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(content):
                    # Check if it's the scanner itself or test fixtures with placeholders
                    if "FORBIDDEN_PATTERNS" in content or "change_me" in content:
                        continue
                    violations.append(f"Potential secret pattern match in: {file_path}")
        except Exception:
            continue

    return violations


def main() -> int:
    print("Running InsurAI Secret & Hygiene Scanner...")
    root = Path(__file__).resolve().parent.parent

    tracked_violations = check_git_tracked_files()
    content_violations = scan_file_contents(root)

    all_violations = tracked_violations + content_violations
    if all_violations:
        print("\n[FAILED] Secret scanner detected security issues:")
        for v in all_violations:
            print(f"  - {v}")
        return 1

    print("[PASSED] No secrets or forbidden files detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
