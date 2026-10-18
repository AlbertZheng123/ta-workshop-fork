"""Expose a small, allowlisted workshop tool surface over MCP stdio."""

from mcp.server.mcpserver import MCPServer

from tools import repository, qa, github

mcp = MCPServer("WorkshopTools")


@mcp.tool()
def read_coding_guidelines() -> str:
    """Read persistent team conventions, not automatically learned memory."""
    return (repository.ROOT / "docs/coding_guidelines.md").read_text()


@mcp.tool()
def get_repo_structure() -> str:
    """List only the app and test files available to the agents."""
    return "\n".join(repository.READABLE)


@mcp.tool()
def get_files(file_paths: list[str]) -> str:
    """Read allowlisted source context, never credentials or tooling code."""
    return repository.get_files(file_paths)


@mcp.tool()
def apply_edits(edits: list[dict]) -> str:
    """Replace allowed app files or the separate generated-test file."""
    return repository.apply_edits(edits)


@mcp.tool()
def run_test_suite() -> dict:
    """Run baseline, acceptance, and feature tests in a restricted container."""
    return qa.run_test_suite()


@mcp.tool()
def get_repository_diff() -> str:
    """Collect changed app files and include untracked feature tests."""
    return repository.get_repository_diff()


@mcp.tool()
def fetch_github_issue(issue_number: int) -> str:
    """Fetch the approved issue, or use the fixed local priority exercise."""
    return github.fetch_github_issue(issue_number)


@mcp.tool()
def publish_pull_request(issue_number: int, summary: str) -> str:
    """Publish a draft on Actions; local runs only return a mock result."""
    return github.publish_pull_request(issue_number, summary)


if __name__ == "__main__":
    # stdout belongs to the MCP protocol; diagnostics belong on stderr.
    mcp.run()
