"""Run an explicit workshop mode, or check prerequisites without API calls."""

import argparse
import os
import subprocess

from orchestrator import run_single_agent_pipeline, run_multi_agent_pipeline
from tools import qa, repository


def preflight():
    """Check the key, Docker image, and clean app baseline before spending."""
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY using your approved course access")
    subprocess.run(["docker", "image", "inspect", qa.IMAGE], check=True,
                   capture_output=True, timeout=15)
    if repository.get_repository_diff().strip():
        raise RuntimeError("Use a fresh clean baseline for each demo mode")


def main(argv=None) -> int:
    """Return a non-zero exit status when setup or any pipeline stage fails."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("single", "multi"))
    parser.add_argument("--issue", type=int, default=42)
    parser.add_argument("--check", action="store_true",
                        help="check setup only; do not call the model")
    args = parser.parse_args(argv)
    try:
        preflight()
        if args.check:
            print("Preflight passed; no model request made.")
            return 0
        mode = args.mode
        if mode is None:
            choice = input("Choose 1 (single) or 2 (multi): ").strip()
            if choice not in {"1", "2"}:
                raise ValueError("Choose 1 or 2")
            mode = "single" if choice == "1" else "multi"
        runner = (run_single_agent_pipeline if mode == "single"
                  else run_multi_agent_pipeline)
        runner(args.issue)
        return 0
    except (Exception, KeyboardInterrupt) as error:
        print(f"Workshop stopped: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
