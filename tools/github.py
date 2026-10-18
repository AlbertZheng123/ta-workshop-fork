"""Local mock issue/PR behavior and explicit GitHub Actions publishing."""

import json
import os
import textwrap
import urllib.request
import uuid

from tools import repository


def request_github(path: str, payload=None) -> dict:
    """Use the current GitHub host without printing credentials or API bodies."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repo or not token:
        raise RuntimeError("GITHUB_REPOSITORY and GITHUB_TOKEN are required")
    api_base = os.getenv("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    if not api_base.startswith("https://"):
        raise RuntimeError("GitHub API must use HTTPS")
    request = urllib.request.Request(
        f"{api_base}/repos/{repo}/{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json",
                 "User-Agent": "CS3300-Workshop"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch_github_issue(issue_number: int) -> str:
    """Use a fixed local exercise or fetch the numbered Actions issue."""
    if not isinstance(issue_number, int) or issue_number < 1:
        raise ValueError("Issue number must be a positive integer")
    if os.getenv("GITHUB_ACTIONS") != "true":
        return textwrap.dedent("""\
            Title: Add task priority
            Body:
            - Tasks can be Low, Medium, or High priority.
            - The user can choose priority when creating a task.
            - The backend stores and returns the priority.
            - The frontend displays the priority.
            - Missing priority defaults to Medium.
            - Existing behavior should continue working.
        """)
    issue = request_github(f"issues/{issue_number}")
    if "pull_request" in issue:
        raise ValueError("Expected an issue, not a pull request")
    return f"Title: {issue['title']}\nBody: {issue.get('body') or ''}"


def publish_pull_request(issue_number: int, summary: str) -> str:
    """Mock locally; create a draft PR on Actions for human review only."""
    if not isinstance(issue_number, int) or issue_number < 1:
        raise ValueError("Issue number must be a positive integer")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("A non-empty implementation summary is required")
    if not repository.get_repository_diff().strip():
        raise RuntimeError("No application changes to publish")
    if os.getenv("GITHUB_ACTIONS") != "true":
        return "LOCAL MOCK: no branch pushed and no pull request created."
    if os.getenv("WORKSHOP_ALLOW_PUBLISH") != "true":
        raise RuntimeError("Workflow publishing is not enabled")
    if not os.getenv("GITHUB_TOKEN") or not os.getenv("GITHUB_REPOSITORY"):
        raise RuntimeError("Missing GitHub publishing credentials")
    staged = repository.git("diff", "--cached", "--name-only").splitlines()
    if any(name not in repository.WRITABLE for name in staged):
        raise RuntimeError("Refusing to commit unrelated staged files")
    branch = f"codex/issue-{issue_number}-{uuid.uuid4().hex[:8]}"
    repository.git("checkout", "-b", branch)
    # Stage only allowed app files, never .env, tools, or workflows.
    paths = [name for name in repository.WRITABLE
             if repository.safe_path(name, repository.WRITABLE).exists()]
    repository.git("add", "--", *paths)
    repository.git("commit", "-m", f"Implement issue #{issue_number}")
    repository.git("push", "-u", "origin", branch)
    result = request_github("pulls", {
        "title": f"Workshop implementation: issue #{issue_number}",
        "body": f"Related to #{issue_number}.\n\n{summary}\n\nHuman review required.",
        "head": branch,
        "base": os.getenv("WORKSHOP_BASE_BRANCH", "main"),
        "draft": True,
    })
    if not result.get("html_url"):
        raise RuntimeError("GitHub did not return a pull request URL")
    return result["html_url"]
