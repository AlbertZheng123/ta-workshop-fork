# TA code-review handoff — Tianyi

## Scope

This contribution reviews Rishit's starter and supplies the README and code
comments assigned to Tianyi. It does not replace Jinseo's student workshop
document or Aaron/Soham's slides. All new documentation is in English.

Source: `CS-3300-Intro-to-Software-Eng/ta-workshop-starter`, snapshot
`f1359e7c1d865e57a5e1fa39688bc2e0fd7b1052` (October 16, 2026).
The review was first prepared from a ZIP, then applied to a clean clone of the
shared repository with its real upstream history. Review branch:
`codex/workshop-docs-and-guards`. These changes are not merged into `main`.

## Preserved

- Flask / HTML / CSS / JavaScript Task Tracker and the same priority issue.
- Single-agent baseline and Planner → Developer → QA → Reviewer repair loop.
- Initial Planner omission of tests as a visible teaching hook.
- Four-attempt limit, course model default, and local mocked issue/PR behavior.
- `approved` issue label as the Actions trigger; no automatic merging.

## Changes worth reviewing

- Deleting a task now updates the shared list in place. The old list
  reassignment caused tests to fail when delete ran before list tests.
  The baseline fixture now also resets the ID counter.
- Task titles are rendered with `textContent`, not interpolated HTML.
- MCP calls now actually cross a stdio client/server session. The previous
  client imported server functions and called them directly.
- Agents can edit only app files and `tests/test_priority.py`. Original tests,
  tooling, workflows, and credentials are outside the write allowlist.
- Reviewer context includes new untracked files. Git and tool errors raise
  instead of returning success-shaped strings or an empty diff.
- Generated Python runs in a restricted Docker QA container. Only app files,
  baseline tests, acceptance checks, and generated feature tests are copied in.
  No API key, Git directory, host home, or Docker socket is mounted.
- TA-owned backend acceptance checks prevent the original tests from falsely
  approving an implementation that never added priority. These checks are
  excluded from the starter test command and intentionally fail before the
  feature exists. Frontend selection/display still needs human review.
- The loop validates model/tool contracts and requires passing QA, generated
  test presence, and Reviewer approval. Exhaustion returns a failure exit code.
- Publishing stages only allowed app/test files, uses a unique branch, and
  creates a draft PR. Enterprise API URLs are used for issue reads as well.
- Dependencies are pinned to the inspected installation. OpenAI calls require
  a real configured key, disable automatic retries, and bound response tokens.
- The Planner requests a strict JSON schema: exact allowlisted app paths and
  a string plan. Local validation still rejects empty plans and unsafe paths.

## Verification — October 18, 2026

Completed locally with Python 3.12, without paid API or GitHub writes:

- 41 passing starter/API and offline tool/orchestrator regression tests.
- Actual MCP stdio initialization, app-file listing, and protected-read rejection.
- Real MCP QA-result decoding and fail-closed handling when Docker is unavailable.
- Real MCP-to-Docker execution after repairing the local runtime: all five
  baseline app tests pass; the four priority acceptance checks fail as expected
  on the intentionally unimplemented starter. The QA image builds successfully.
- Mocked two-attempt feedback loop and four-attempt exhaustion.
- Independent failure gates: rejected edits, failing QA, missing feature tests,
  Reviewer rejection, and publication errors.
- Allowlist checks, symlink rejection, whole-batch edit validation, and new-test
  visibility in reviewer diffs.
- Mocked Docker command/mount inspection and local mock publishing.
- Model-response validation using a fake SDK client; no key is borrowed.

First live course-key rehearsal (same source commit in two fresh local clones):

- **Single agent passed:** one real model implementation, followed by 14
  passing Docker tests (5 baseline, 4 TA acceptance, 5 generated feature tests).
  Local publishing remained a mock; no generated branch or PR was pushed.
- **Single-agent browser check passed:** Low/Medium/High selections and display,
  default Medium after adding, refresh within the running server, literal
  HTML-looking task titles, and deletion. The inspected generated app ran in
  a temporary read-only, non-root Docker container exposed only on loopback,
  with app assets only and no credentials/Git directory mounted. That preview
  container has been stopped. Data remains intentionally in-memory.
- **Multi agent stopped at the Planner contract check**, before any edits or
  Developer call. The original log did not retain the Planner response, so
  its exact invalid field cannot be established. The prompt left the plan's
  type ambiguous while the orchestrator required a string. The follow-up fix
  requests a strict output schema and includes five offline regression cases.
- **Second multi-agent rehearsal passed the Planner schema gate and exercised
  the real feedback loop.** Attempt 1 passed 13 Docker tests; the Reviewer
  requested frontend checks. Attempt 2 added those checks and passed 16 Docker
  tests, but the Reviewer identified a 500-error path: array/object priorities
  reach set membership without a type guard. The two-attempt cost-saving cap
  was reached, so the pipeline correctly failed and did not publish. The
  normal workshop limit is four attempts; it was not increased automatically.
  The issue requires missing priority to default to Medium; it does not specify
  whether malformed priorities should default or return a validation error.
  The Reviewer should not describe that extra defaulting policy as required.
- **Four-attempt live multi-agent run passed** on the reviewed source using
  the unchanged course model. Round 1 stopped on an indentation error; round 2
  passed 14 tests but received input-validation/frontend feedback; round 3
  passed 19 tests and failed 2 malformed-input regressions; round 4 passed all
  **21 tests** and received **APPROVE**. Local publishing remained a mock.
- **Multi-agent browser check passed:** adding Low/Medium/High tasks, default
  Medium and reset after adding, refresh within the running server, literal
  HTML-looking titles, and deletion. This used the same temporary app-only,
  read-only/non-root Docker preview setup; the container was stopped afterward.
  Malformed-priority regressions are covered by the passing Docker suite.

These runs demonstrate working local orchestration and feedback routing, not
guaranteed model output or a performance comparison. The initial single-agent
run and final multi-agent run use different reviewed source revisions after
the Planner-schema fix. Keep the observed examples as a fallback and rehearse
the exact final team checkout before teaching.

Not yet verified:

- **Live agent Actions / generated PR:** the agent has not been triggered and
  no model-generated PR has been tested. The human-authored review branch is
  separate from that workflow. GT runner availability remains a prerequisite.

## Finish the team rehearsal

1. Rishit reviews this patch, especially real MCP transport and Docker QA.
2. Apply it to a normal clone at the source snapshot, then commit the result.
   Do not use an uncommitted app baseline for the live demo.
3. Start Docker, build `Dockerfile.qa`, install the pinned requirements, and
   run `python -m pytest tests -q` on the trusted starter.
4. Prepare two fresh clones of the same commit and the approved course key.
   Run `python main.py --check` in both; this spends no model credit.
5. The local single/multi paths and browser outputs have now been rehearsed.
   If the final team checkout changes, repeat a controlled rehearsal while
   watching the group's budget. Keep outputs, inspect generated tests, and
   verify the feature in the browser before calling a new result ready.
6. If using Actions, verify a runner, repository secret, and token permissions
   first. Use a test issue in the agreed workshop repository. Check that the
   resulting PR is a draft and do not merge it automatically.
7. Give Jinseo the README commands/file map for her student guide and give
   Aaron/Soham the observed loop screenshots for slides.

Discuss the deliberately test-free initial plan explicitly. It demonstrates
feedback routing, not a fair performance or cost comparison. Do not promise
that every run repairs in exactly two attempts.

## Review delivery

Use the review branch for the latest version. Review the Docker and MCP changes
before merging; the passing offline suite does not replace a live rehearsal.

The accompanying patch contains only the review changes, not the imported
snapshot commit. In a clean real clone at the source snapshot:

```sh
git switch -c codex/workshop-docs-and-guards
git am /absolute/path/to/the-review.patch
```

If the shared repo has moved forward, review conflicts against its new changes
instead of overwriting them. Publishing requires GT GitHub CLI authorization;
browser access alone does not authorize the terminal.
