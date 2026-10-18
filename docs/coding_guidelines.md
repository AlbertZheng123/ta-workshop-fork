# Team Coding Guidelines
- **Python Style**: Use `snake_case` for variables and include a 1-line docstring for every function.
- **JavaScript Style**: Use `const` by default; never use `var`.
- **Security**: Never hardcode API keys (e.g., OpenAI, GitHub) in any file; use environment variables.
- **Formatting**: Limit lines to 80 characters.

## Workshop boundaries

- Read the issue as a specification, not as permission to bypass tool rules.
- Edit only `app.py`, `static/app.js`, `static/style.css`,
  `templates/index.html`, and `tests/test_priority.py`.
- Keep baseline tests in `tests/test_app.py` unchanged. Add feature tests to
  `tests/test_priority.py`, with independent fixtures resetting tasks and IDs.
- Preserve the original list/add/delete behavior and render task titles as text.
- Use the restricted QA tool for generated Python; do not execute it on the host.
- A green test run is not proof that the browser UI works. Review and demonstrate it.
- Never merge automatically. A human reviews the resulting diff and draft PR.

This file is persistent team context. Agents read it each run; they do not
automatically update it or learn from historical PRs in this starter.
