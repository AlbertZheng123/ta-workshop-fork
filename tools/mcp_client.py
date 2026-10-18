"""Synchronous entry point backed by a real MCP stdio client session."""

import asyncio
import json
import os
import sys

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from tools.repository import ROOT

TOOL_NAMES = {
    "read_coding_guidelines", "get_repo_structure", "get_files", "apply_edits",
    "run_test_suite", "get_repository_diff", "fetch_github_issue",
    "publish_pull_request",
}


async def _execute(tool_name: str, arguments: dict):
    """Initialize, call, and close one session; favor clarity over pooling."""
    names = ("PATH", "HOME", "TMPDIR", "SYSTEMROOT", "WINDIR",
             "GITHUB_ACTIONS", "GITHUB_REPOSITORY", "GITHUB_TOKEN",
             "GITHUB_API_URL", "WORKSHOP_ALLOW_PUBLISH",
             "WORKSHOP_BASE_BRANCH", "DOCKER_HOST", "DOCKER_CONTEXT",
             "DOCKER_CONFIG")
    # The OpenAI key stays in the parent, outside the tool server.
    environment = {name: os.environ[name] for name in names if name in os.environ}
    server = StdioServerParameters(
        command=sys.executable, args=["-m", "tools.mcp_server"],
        cwd=ROOT, env=environment,
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                tool_name, arguments, read_timeout_seconds=90,
            )
            if result.is_error:
                details = " ".join(getattr(item, "text", "")
                                   for item in result.content)
                error = f"Tool {tool_name} failed: {details}"
                value = None
            else:
                error = None
                value = result.structured_content
                if isinstance(value, dict) and set(value) == {"result"}:
                    value = value["result"]
                if value is None:
                    texts = [item.text for item in result.content
                             if item.type == "text"]
                    if len(texts) != 1:
                        error = f"Unexpected result from {tool_name}"
                    else:
                        value = texts[0]
    # Raise after context shutdown so a tool error is not hidden in TaskGroups.
    if error:
        raise RuntimeError(error)
    # Generic dict return annotations may be serialized only as text by MCP.
    if tool_name == "run_test_suite" and isinstance(value, str):
        value = json.loads(value)
    return value


def execute_mcp_tool(tool_name: str, arguments: dict = None):
    """Raise on unknown tools, transport errors, or server-side failures."""
    if tool_name not in TOOL_NAMES:
        raise ValueError(f"Unknown workshop tool: {tool_name}")
    return asyncio.run(_execute(tool_name, arguments or {}))
