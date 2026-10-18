# CS3300 Agent Workshop Starter

A small Flask task tracker for comparing a single-agent implementation with a
Planner → Developer → QA → Reviewer feedback loop. The exercise is to add task
priority: **Low, Medium, High**, with **Medium** as the default.

The starter intentionally does **not** implement priority. Task data is stored
in memory and resets when the app restarts. No GCP setup or database is needed
for this workshop. This is separate from Project 1 and its grading requirements.

## 1. Run the starter first — no API key needed

Use Python **3.12**, Git, and a terminal in the repository root.

macOS / Linux:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest tests -q
python -m flask --app app run --port 5001
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest tests -q
python -m flask --app app run --port 5001
```

If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` in place of
`python`; changing your system execution policy is not required.

Open <http://localhost:5001>. Confirm that you can list, add, and delete tasks.
There is no priority selector yet. Stop the server with **Ctrl+C**.

`python app.py` also works, but uses port 5000. Port 5001 avoids a common macOS
port conflict. Run host-side pytest only on the trusted starter; after an agent
edits Python files, use the isolated QA tool described below.

## 2. Prepare the AI demo

Start Docker Desktop, then build the QA image once:

```sh
docker build -f Dockerfile.qa -t cs3300-workshop-qa:local .
```

This build downloads dependencies. Test containers subsequently run with no
network, no API credentials, and an app-only read-only mount. They cannot see
the host checkout's `.git`, `.env`, agent code, or Docker socket.

Use your **course-provided OpenAI access and an allowed model**. Do not borrow
another student's key or put a key in a prompt, screenshot, repository, or PR.
The default remains Rishit's `gpt-5.6-luna`; it still needs to be enabled for
your course project. A default model name is not a guarantee of account access.

macOS zsh — enter the key without displaying it:

```sh
read -s "OPENAI_API_KEY?Paste your course API key: "
export OPENAI_API_KEY
export LLM_MODEL="gpt-5.6-luna"
```

Windows PowerShell:

```powershell
$workshopKey = Read-Host "Paste your course API key" -AsSecureString
$env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new("", $workshopKey).Password
$env:LLM_MODEL = "gpt-5.6-luna"
```

The code reads environment variables; it does **not** load `.env` automatically.
For macOS bash/Linux, use `read -s -p "API key: " OPENAI_API_KEY` instead of the
zsh `read` line, then export the variable as above.

Check prerequisites without making a model request:

```sh
python main.py --check
```

Preflight requires a key, an available QA image, and no changes to the demo's
app/test files. It does **not** validate model access or perform a paid request.

## 3. Run one mode

Start each mode from a **separate clean clone of the same starter commit**.
Do not run multi-agent on top of the single-agent output. Keep the first result
for comparison; do not discard local work to reset the repository.

```sh
python main.py --mode single
```

or, in the other clean clone:

```sh
python main.py --mode multi
```

`python main.py` offers the original interactive choice. Locally, issue number
42 is a placeholder: the tool always returns the fixed priority exercise.
`--issue 1` fetches a real issue only when running in GitHub Actions.

| Stage | Single agent | Multi-agent |
| --- | --- | --- |
| Context | Issue, app files, guidelines | Same issue and guidelines; Planner selects initial files |
| Implementation | One model call, including feature tests | Planner call, then Developer call |
| QA | Protected baseline + acceptance + generated tests | Same checks after every attempt |
| Review / repair | Human reviews the result; no automated repair | Reviewer gives feedback; Developer gets current files and test output |
| Finish | QA must pass and collect new feature tests | QA, collected feature tests, and Reviewer approval must all pass |

The multi-agent flow stops after at most **4 implementation attempts**. That
means up to **9 model requests**: one Planner call and up to four Developer /
Reviewer pairs. Single-agent uses one. Each call has a completion-token limit;
this is **not a dollar-spend guarantee**. Watch the course group's $10 budget
and avoid repeatedly rerunning a failed demo.

The Planner uses a strict JSON output schema for exact app paths and a string
plan. Local validation remains enabled; invalid model output stops the run
before files are edited. There is no automatic schema-error retry or model
substitution.

**Teaching hook:** the initial Planner prompt deliberately omits test work so
that the Reviewer can request tests. This is a controlled feedback-loop
demonstration, not evidence that multi-agent systems outperform single agents.
The number of attempts and the model's exact edits are not deterministic.

## 4. Inspect the result

Local success prints **LOCAL MOCK**. It does not create a branch, push, or open
a PR. Changes remain in your local app files for inspection.

```sh
git status --short
git diff -- app.py static/app.js static/style.css templates/index.html
git ls-files --others --exclude-standard
```

New untracked tests will not appear in ordinary `git diff`. Open
`tests/test_priority.py`, or use the MCP diff tool, which includes new tests:

```sh
python -c 'from tools.mcp_client import execute_mcp_tool; print(execute_mcp_tool("get_repository_diff"))'
```

Before running the changed app on your host, inspect the Python diff. Then
confirm priority selection, display, persistence across GET requests, default
Medium, and the original add/delete behavior in the browser. Automated backend
tests do not prove the UI works. A human still decides whether the result is
ready to merge.

To repeat isolated QA after inspecting or fixing code:

```sh
python -c 'from tools.mcp_client import execute_mcp_tool; print(execute_mcp_tool("run_test_suite"))'
```

## How the code fits together

| File | Purpose |
| --- | --- |
| `app.py`, `templates/`, `static/` | Starter API and browser UI |
| `main.py` | Mode selection, preflight, and non-zero failure exit status |
| `orchestrator.py` | Bounded plan / develop / test / review loop |
| `agents/` | Standardized prompts for the four roles |
| `tools/llm.py` | Bounded JSON-mode OpenAI call; no call at import time |
| `tools/mcp_client.py`, `tools/mcp_server.py` | Real stdio MCP session and eight tools |
| `tools/repository.py` | File allowlist, validated edits, complete reviewer diff |
| `tools/qa.py`, `Dockerfile.qa` | Disposable, restricted test execution |
| `tools/github.py` | Local mocks and Actions-only draft PR publishing |
| `tests/test_app.py` | Protected tests for original behavior |
| `tests/test_priority.py` | AI-generated feature tests; absent in the starter |
| `acceptance/test_priority_contract.py` | TA-owned backend checks of the priority spec |
| `tests/test_workshop.py` | Offline checks of tools and orchestration |
| `docs/coding_guidelines.md` | Persistent team context supplied to the agents |

MCP is the tool transport, not an extra model. Python orchestration determines
tool order; the models produce plans, edits, and review decisions. For clarity,
this implementation opens and closes one MCP session per tool call.
Guidelines are persistent context, **not** an automatically learned memory.

The agents can edit only four app files and `tests/test_priority.py`. They
cannot rewrite the baseline tests, acceptance tests, tools, workflows, or
credentials. QA copies only the app and selected tests into its container.
These are teaching guardrails, not a production security boundary against
arbitrary malicious code or proof that an LLM review is correct.

Acceptance tests intentionally fail on the unmodified starter. Ordinary
`pytest tests` excludes them. The feature QA stage includes them to prevent
the original five tests from giving a false green result when priority is
missing. They check the original spec, not a new grading rubric.

## Optional GitHub Actions demo — TA-controlled

The workflow runs the **multi-agent** path when a repository member adds the
`approved` label to an issue. It uses the repository's `OPENAI_API_KEY` secret
and `GITHUB_TOKEN`; do not put secrets in issue text.

After baseline checks and QA image preparation, it runs the agent. Success
creates a **draft PR** on a unique branch. It never auto-merges. Failure exits
non-zero and does not deliberately proceed to publishing. If a push succeeds
but the PR API request fails, inspect that branch before rerunning.

`GITHUB_API_URL` is respected for both issue reads and PR creation, including
GitHub Enterprise. A runner with Docker and outbound API access is required.
GT GitHub hosted-runner availability must be checked by the TA team; a local
demo works without a runner. Do not enable a personal paid runner or move
course data to another host without team approval.

Adding the label is permission to spend API credit and create a draft, not
permission to merge. Keep this action under TA control during the workshop.

## Troubleshooting

| If you see… | Check / next step |
| --- | --- |
| `python` / `pip` not found | Use Python 3.12 and activate the venv; use `python -m pip` |
| Import / dependency errors | Install the pinned requirements in the same venv that runs `main.py` |
| Port 5000 already used | Use the Flask command with `--port 5001` |
| Docker daemon unavailable | Start Docker Desktop and wait for it to be ready |
| QA image not found | Run the Docker build command before the agent |
| Preflight reports app changes | Use another clean baseline clone; preserve the existing output |
| API authentication / model-access error | Check course project/key and allowed models; do not print the key |
| Malformed / truncated JSON | Stop and inspect the prompt/result size; do not blindly rerun repeatedly |
| Missing feature tests / Reviewer requests changes | In multi-agent, inspect the next repair attempt and its actual test output |
| Four attempts exhausted | Inspect the diff and make a human decision; publication has not succeeded |
| Actions queued indefinitely | Check runner availability; use the local demo if no runner is available |
| Green tests but UI wrong | Review the frontend diff and demonstrate the UI; backend tests are not enough |

For the TA review status and remaining rehearsal checks, see
[docs/ta-handoff.md](docs/ta-handoff.md).

API references: [OpenAI JSON mode](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat)
and [Chat Completions parameters](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).
