# Instructions for AI coding agents

## Every pull request needs a changelog fragment

Do not edit `CHANGELOG.md`. Add a new file in `changelog.d/` instead. CI fails without one. Dependabot and release pull requests do not need one.

- **Name:** `changelog.d/+<short-description>.<type>.md`
- **Type:** `breaking`, `added`, `changed`, `deprecated`, `removed`, `fixed`, `security`, or `repository` (CI, tooling, tests, docs)
- **Content:** one sentence on one line, with no heading and no leading `- `

Example, `changelog.d/+lizard-exit-code.fixed.md`:

```markdown
Fix lizard hook only considering the exit code of the last file
```

Use one file per change. Do not run `towncrier build`, and do not touch other fragments.

## Development

- Test: `python -m pip install -e .[test]`, then `python -m pytest` (unit tests) and `python -m pytest tests/integration -n auto` (needs CMake and the C/C++ tools)
- Lint: `pre-commit run --all-files`
- New hooks and options need tests and an entry in `README.md`
- Do not tag, set versions or publish by hand: the release workflows do that
