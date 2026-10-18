"""Run generated code in a restricted Docker container, not on the host."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

from tools import repository

IMAGE = "cs3300-workshop-qa:local"


def run_test_suite() -> dict:
    """Test a disposable app-only copy without API keys or host Git data."""
    name = f"cs3300-qa-{uuid.uuid4().hex[:12]}"
    try:
        with tempfile.TemporaryDirectory(prefix="cs3300-qa-") as directory:
            target = Path(directory)
            names = (*repository.READABLE, "acceptance/test_priority_contract.py")
            for filename in names:
                # Acceptance tests are trusted files, outside the edit allowlist.
                source = (repository.ROOT / filename if filename.startswith(
                    "acceptance/") else repository.safe_path(filename))
                if not source.exists():
                    if filename == repository.FEATURE_TEST:
                        continue
                    raise FileNotFoundError(filename)
                destination = target / filename
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
                destination.chmod(0o644)
            for path in target.rglob("*"):
                if path.is_dir():
                    path.chmod(0o755)
            target.chmod(0o755)
            command = [
                "docker", "run", "--rm", "--name", name,
                "--network", "none", "--read-only", "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges", "--pids-limit", "64",
                "--memory", "256m", "--cpus", "1", "--user", "65534:65534",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=32m",
                "--mount", f"type=bind,source={target},target=/workspace,readonly",
                "--env", "PYTHONDONTWRITEBYTECODE=1",
                "--env", "PYTHONPATH=/workspace", IMAGE,
                "tests/test_app.py", "acceptance/test_priority_contract.py",
            ]
            if (target / repository.FEATURE_TEST).exists():
                command.append(repository.FEATURE_TEST)
            command.extend(["-v", "-p", "no:cacheprovider"])
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=45,
            )
            return {
                "passed": result.returncode == 0,
                "output": (result.stdout + "\n" + result.stderr)[-20_000:],
                "feature_tests_present": (
                    (target / repository.FEATURE_TEST).exists()
                    and f"{repository.FEATURE_TEST}::" in result.stdout),
            }
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"passed": False, "output": f"QA unavailable: {error}",
                "feature_tests_present": False}
    finally:
        # A timed-out docker client can leave its container running.
        try:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True,
                           timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            pass
