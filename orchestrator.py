"""Coordinate roles and stop unless tests AND review permit publication."""

from tools.mcp_client import execute_mcp_tool
from tools.contracts import require_implementation, require_tests
from tools.repository import APP_FILES, READABLE
from agents.single_agent import run_single_agent
from agents.planner import create_plan
from agents.developer import implement_feature
from agents.reviewer import review_feature


def run_single_agent_pipeline(issue_number: int):
    """Expose the single-agent baseline through the same entry module."""
    return run_single_agent(issue_number)


def run_multi_agent_pipeline(issue_number: int, max_attempts: int = 4):
    """Run a bounded plan/develop/test/review loop, raising on failure."""
    if not isinstance(max_attempts, int) or not 1 <= max_attempts <= 4:
        raise ValueError("max_attempts must be between 1 and 4")
    print(f"--- Multi-agent pipeline: issue #{issue_number} ---")
    issue = execute_mcp_tool("fetch_github_issue", {"issue_number": issue_number})
    structure = execute_mcp_tool("get_repo_structure")
    guidelines = execute_mcp_tool("read_coding_guidelines")
    plan = create_plan(issue, structure)
    if (not isinstance(plan, dict)
            or not isinstance(plan.get("plan"), str)
            or not isinstance(plan.get("files_to_modify"), list)
            or not plan["files_to_modify"]
            or any(path not in APP_FILES for path in plan["files_to_modify"])):
        raise ValueError("Planner must name allowed app files and a plan")
    feedback, test_output = None, None
    summaries = []
    for attempt in range(1, max_attempts + 1):
        print(f"\n--- Attempt {attempt}/{max_attempts} ---")
        # Always include the existing generated tests during a repair attempt.
        paths = plan["files_to_modify"] if attempt == 1 else list(READABLE)
        context = execute_mcp_tool("get_files", {"file_paths": paths})
        implementation = require_implementation(implement_feature(
            issue, plan, context, guidelines, feedback, test_output,
        ))
        execute_mcp_tool("apply_edits", {"edits": implementation["edits"]})
        summaries.append(f"Attempt {attempt}: {implementation['summary']}")
        tests = require_tests(execute_mcp_tool("run_test_suite"))
        test_output = tests["output"]
        print(f"Tests: {'PASS' if tests['passed'] else 'FAIL'}\n{test_output}")
        diff = execute_mcp_tool("get_repository_diff")
        review = review_feature(issue, plan, diff, tests, guidelines)
        if (not isinstance(review, dict)
                or review.get("status") not in {
                    "APPROVE", "REQUEST_CHANGES", "REQUEST_MORE_TESTS"}
                or not isinstance(review.get("feedback"), str)):
            raise ValueError("Reviewer returned an invalid decision")
        feedback = review["feedback"]
        print(f"Review: {review['status']}\n{feedback}")
        if not tests["feature_tests_present"]:
            feedback += "\nAdd independent feature tests in tests/test_priority.py."
        if (tests["passed"] and tests["feature_tests_present"]
                and review["status"] == "APPROVE"):
            publication = execute_mcp_tool("publish_pull_request", {
                "issue_number": issue_number, "summary": "\n".join(summaries),
            })
            print(publication)
            return {"attempts": attempt, "tests": tests, "review": review,
                    "publication": publication}
    raise RuntimeError(f"No approved, tested implementation after {max_attempts} attempts")
