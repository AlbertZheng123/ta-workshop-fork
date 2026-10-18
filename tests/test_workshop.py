"""Offline regression tests: no paid model calls, pushes, or live GitHub API."""

from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

import app as app_module
import main
import orchestrator
from agents import single_agent
from tools import github, llm, qa, repository
from tools.mcp_client import execute_mcp_tool


@pytest.fixture
def scratch_repo(tmp_path, monkeypatch):
    """Copy trusted fixtures into a disposable local Git checkout."""
    root = repository.ROOT
    for name in (*repository.READABLE, "acceptance/test_priority_contract.py"):
        source = root / name
        if source.exists():
            destination = tmp_path / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    monkeypatch.setattr(repository, "ROOT", tmp_path)
    repository.git("init", "-q")
    repository.git("config", "user.name", "Workshop Test")
    repository.git("config", "user.email", "test@example.invalid")
    repository.git("add", ".")
    repository.git("commit", "-qm", "Trusted baseline")
    return tmp_path


def test_delete_keeps_shared_list_and_resettable_ids():
    """Prevent the original order-dependent task list regression."""
    shared = app_module.tasks
    saved, counter = list(shared), app_module.next_id
    try:
        shared[:] = [{"id": 1, "title": "One"}]
        app_module.app.test_client().delete("/api/tasks/1")
        assert app_module.tasks is shared
        assert shared == []
    finally:
        shared[:] = saved
        app_module.next_id = counter


@pytest.mark.parametrize("path", [
    ".env", "/tmp/outside.py", "../app.py", "tools/llm.py",
    "tests/test_app.py", ".github/workflows/agent-feature.yml",
])
def test_reject_protected_edits(scratch_repo, path):
    """Only app files and the separate feature-test file may be edited."""
    with pytest.raises(ValueError):
        repository.apply_edits([{"file_path": path, "content": "changed"}])


def test_invalid_batch_does_not_partially_write(scratch_repo):
    """Validate all edits before applying the first one."""
    before = (scratch_repo / "app.py").read_text()
    with pytest.raises(ValueError):
        repository.apply_edits([
            {"file_path": "app.py", "content": "changed"},
            {"file_path": ".env", "content": "no"},
        ])
    assert (scratch_repo / "app.py").read_text() == before


def test_reject_symlink(scratch_repo, tmp_path):
    """Do not follow an allowed filename that points outside the checkout."""
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.write_text("sentinel")
    path = scratch_repo / repository.FEATURE_TEST
    path.symlink_to(outside)
    with pytest.raises(ValueError):
        repository.get_files([repository.FEATURE_TEST])


def test_diff_includes_untracked_tests(scratch_repo):
    """A new test must be visible to the reviewer before staging."""
    repository.apply_edits([{
        "file_path": repository.FEATURE_TEST,
        "content": "def test_priority():\n    assert True\n",
    }])
    assert "NEW FILE: tests/test_priority.py" in repository.get_repository_diff()


def test_git_error_is_not_empty_diff(tmp_path, monkeypatch):
    """A missing Git repository is a failure, not evidence of no changes."""
    monkeypatch.setattr(repository, "ROOT", tmp_path)
    with pytest.raises(Exception):
        repository.get_repository_diff()


@pytest.fixture
def fake_pipeline(monkeypatch):
    """Replace all external work while recording orchestration decisions."""
    state = {"tools": [], "qa": [], "reviews": [], "contexts": []}

    def tool(name, args=None):
        """Return controlled tool results without running code or publishing."""
        state["tools"].append(name)
        if name == "fetch_github_issue":
            return "Add priority"
        if name == "get_repo_structure":
            return "\n".join(repository.READABLE)
        if name == "read_coding_guidelines":
            return "Keep baseline tests"
        if name == "get_files":
            state["contexts"].append(args["file_paths"])
            return "Source context"
        if name == "apply_edits":
            if state.get("edit_error"):
                raise RuntimeError("Edit rejected")
            return "Successfully applied 1 edits."
        if name == "run_test_suite":
            return state["qa"].pop(0)
        if name == "get_repository_diff":
            return "Diff including tests"
        if name == "publish_pull_request":
            if state.get("publish_error"):
                raise RuntimeError("Publish failed")
            return "LOCAL MOCK"
        raise AssertionError(name)

    monkeypatch.setattr(orchestrator, "execute_mcp_tool", tool)
    monkeypatch.setattr(single_agent, "execute_mcp_tool", tool)
    monkeypatch.setattr(orchestrator, "create_plan", lambda *args: {
        "files_to_modify": ["app.py"], "plan": "Add priority",
    })
    implementation = {"edits": [{"file_path": "app.py", "content": "code"}],
                      "summary": "Implemented priority"}
    monkeypatch.setattr(orchestrator, "implement_feature",
                        lambda *args: implementation)
    monkeypatch.setattr(single_agent, "call_llm_json",
                        lambda *args: implementation)
    monkeypatch.setattr(orchestrator, "review_feature",
                        lambda *args: state["reviews"].pop(0))
    return state


def qa_result(passed=True, feature=True):
    """Build explicit QA contracts for offline flow tests."""
    return {"passed": passed, "output": "Test output",
            "feature_tests_present": feature}


def review_result(status="APPROVE"):
    """Build an explicit reviewer decision."""
    return {"status": status, "feedback": "Please check feature tests"}


@pytest.mark.parametrize("passed,feature,status", [
    (False, True, "APPROVE"), (True, False, "APPROVE"),
    (True, True, "REQUEST_CHANGES"),
])
def test_failed_gate_never_publishes(fake_pipeline, passed, feature, status):
    """Tests, new test presence, and reviewer approval are independent gates."""
    fake_pipeline["qa"] = [qa_result(passed, feature)]
    fake_pipeline["reviews"] = [review_result(status)]
    with pytest.raises(RuntimeError):
        orchestrator.run_multi_agent_pipeline(1, max_attempts=1)
    assert "publish_pull_request" not in fake_pipeline["tools"]


def test_repair_loop_includes_current_tests(fake_pipeline):
    """The second developer attempt can see and preserve its previous tests."""
    fake_pipeline["qa"] = [qa_result(feature=False), qa_result()]
    fake_pipeline["reviews"] = [review_result("REQUEST_MORE_TESTS"),
                                review_result()]
    result = orchestrator.run_multi_agent_pipeline(1)
    assert result["attempts"] == 2
    assert repository.FEATURE_TEST in fake_pipeline["contexts"][1]
    assert fake_pipeline["tools"].count("publish_pull_request") == 1


def test_edit_failure_stops_before_qa(fake_pipeline):
    """A failed write must not continue into tests or publication."""
    fake_pipeline["edit_error"] = True
    with pytest.raises(RuntimeError, match="Edit rejected"):
        orchestrator.run_multi_agent_pipeline(1)
    assert "run_test_suite" not in fake_pipeline["tools"]


def test_attempt_limit_is_enforced(fake_pipeline):
    """Stop after four attempts instead of silently returning success."""
    fake_pipeline["qa"] = [qa_result(False)] * 4
    fake_pipeline["reviews"] = [review_result()] * 4
    with pytest.raises(RuntimeError, match="after 4 attempts"):
        orchestrator.run_multi_agent_pipeline(1)
    assert fake_pipeline["tools"].count("run_test_suite") == 4


def test_publication_error_propagates(fake_pipeline):
    """A green review does not turn a GitHub failure into success."""
    fake_pipeline["qa"] = [qa_result()]
    fake_pipeline["reviews"] = [review_result()]
    fake_pipeline["publish_error"] = True
    with pytest.raises(RuntimeError, match="Publish failed"):
        orchestrator.run_multi_agent_pipeline(1)


def test_single_agent_uses_same_qa_gate(fake_pipeline):
    """The single-agent path must not publish when tests fail."""
    fake_pipeline["qa"] = [qa_result(False)]
    with pytest.raises(RuntimeError):
        single_agent.run_single_agent(1)
    assert "publish_pull_request" not in fake_pipeline["tools"]


def test_cli_failure_returns_nonzero(monkeypatch):
    """Actions must receive failure rather than an exit-zero print message."""
    def fail():
        """Simulate a prerequisite error without Docker or API calls."""
        raise RuntimeError("Unavailable")
    monkeypatch.setattr(main, "preflight", fail)
    assert main.main(["--mode", "multi"]) == 1


def test_model_key_is_required(monkeypatch):
    """Missing credentials fail before an SDK network request."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        llm.call_llm_json("Return JSON")


@pytest.mark.parametrize("content,finish", [
    ("not json", "stop"), ("[]", "stop"), ("{}", "length"),
])
def test_reject_invalid_model_output(monkeypatch, content, finish):
    """Malformed JSON and truncated responses cannot advance the pipeline."""
    class FakeClient:
        """Stand-in SDK context manager; never contacts OpenAI."""

        def __init__(self, **kwargs):
            """Expose the expected chat completion shape."""
            self.chat = SimpleNamespace(completions=self)

        def __enter__(self):
            """Return the fake client."""
            return self

        def __exit__(self, *args):
            """Close without side effects."""

        def create(self, **kwargs):
            """Return a chosen response and check cost/privacy options."""
            assert kwargs["store"] is False
            assert kwargs["max_completion_tokens"] == 8000
            return SimpleNamespace(choices=[SimpleNamespace(
                finish_reason=finish,
                message=SimpleNamespace(content=content),
            )])

    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-not-a-real-key")
    monkeypatch.setattr(llm, "OpenAI", FakeClient)
    with pytest.raises((ValueError, RuntimeError)):
        llm.call_llm_json("Return JSON")


def test_real_mcp_read_round_trip():
    """Exercise actual stdio initialization and result decoding offline."""
    structure = execute_mcp_tool("get_repo_structure")
    assert isinstance(structure, str)
    assert "app.py" in structure
    assert ".env" not in structure


def test_real_mcp_rejects_protected_read():
    """Server errors must cross the transport as failures, not success text."""
    with pytest.raises(RuntimeError, match="get_files failed"):
        execute_mcp_tool("get_files", {"file_paths": [".env"]})


def test_real_mcp_qa_result_is_an_object():
    """Decode QA's JSON text even when Docker is unavailable or tests fail."""
    result = execute_mcp_tool("run_test_suite")
    assert isinstance(result, dict)
    assert type(result["passed"]) is bool
    assert isinstance(result["output"], str)


def test_qa_copies_only_app_files(scratch_repo, monkeypatch):
    """Inspect Docker inputs without starting a daemon or executing AI code."""
    (scratch_repo / ".env").write_text("SENTINEL_SECRET=not-a-real-key")
    calls = []

    def run(command, **kwargs):
        """Inspect the disposable read-only app mount and command flags."""
        calls.append(command)
        if "run" in command:
            mount = command[command.index("--mount") + 1]
            copied = Path(mount.split("source=")[1].split(",")[0])
            assert not (copied / ".env").exists()
            assert not (copied / ".git").exists()
            assert not (copied / "tools").exists()
            assert (copied / "acceptance/test_priority_contract.py").exists()
            assert command[command.index("--network") + 1] == "none"
            assert "--read-only" in command
            assert "OPENAI_API_KEY" not in " ".join(command)
            assert "GITHUB_TOKEN" not in " ".join(command)
        return SimpleNamespace(returncode=0, stdout="Passed", stderr="")

    monkeypatch.setattr(qa.subprocess, "run", run)
    assert qa.run_test_suite()["passed"] is True
    assert calls[-1][:3] == ["docker", "rm", "-f"]


def test_local_publish_is_mock(scratch_repo, monkeypatch):
    """A local successful run must not push or contact GitHub."""
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    (scratch_repo / "app.py").write_text("# harmless fixture change\n")
    assert "LOCAL MOCK" in github.publish_pull_request(1, "Summary")


def test_actions_publish_needs_explicit_permission(scratch_repo, monkeypatch):
    """Only the publishing workflow may create a draft PR."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.delenv("WORKSHOP_ALLOW_PUBLISH", raising=False)
    (scratch_repo / "app.py").write_text("# harmless fixture change\n")
    with pytest.raises(RuntimeError, match="not enabled"):
        github.publish_pull_request(1, "Summary")


def test_github_uses_enterprise_api_base(monkeypatch):
    """Issue fetching must use GITHUB_API_URL, not hardcoded github.com."""
    import io
    monkeypatch.setenv("GITHUB_REPOSITORY", "course/workshop")
    monkeypatch.setenv("GITHUB_TOKEN", "offline-test-token")
    monkeypatch.setenv("GITHUB_API_URL", "https://github.example.edu/api/v3")

    def urlopen(request, **kwargs):
        """Inspect a fake request without sending it."""
        assert request.full_url.startswith("https://github.example.edu/api/v3/")
        return io.BytesIO(b'{"title":"Priority","body":"Example"}')

    monkeypatch.setattr(github.urllib.request, "urlopen", urlopen)
    assert github.request_github("issues/1")["title"] == "Priority"
