# AGENTS.md

## Scope

These instructions apply to `/Users/wese/Repos/github.com/rwese/ha_epex_spot_sensor`.

## Structure

- `/Users/wese/Repos/github.com/rwese/ha_epex_spot_sensor/custom_components/epex_spot_sensor/` contains the Home Assistant integration.
- `/Users/wese/Repos/github.com/rwese/ha_epex_spot_sensor/custom_components/epex_spot/` contains vendored EPEX Spot support code.
- `/Users/wese/Repos/github.com/rwese/ha_epex_spot_sensor/tests/` contains pytest tests.
- `/Users/wese/Repos/github.com/rwese/ha_epex_spot_sensor/Spec/` contains implementation notes and backlog specs.

## Commands

- Create the test environment with Python 3.13:
  `uv venv --python /opt/homebrew/bin/python3.13 .venv`
- Install pinned test dependencies:
  `uv pip install --prerelease=allow -r requirements_test.txt`
- Run tests:
  `.venv/bin/python -m pytest`
- Run quality gates:
  `pre-commit run --all-files`
- Optional quick syntax check:
  `python3 -m compileall custom_components tests`

## Testing Notes

- Use Python 3.13 for the pinned Home Assistant test stack. Python 3.14 is currently incompatible with `orjson==3.10.12` through PyO3.
- `requirements_test.txt` pins `pytest-homeassistant-custom-component==0.13.205`.
- `pytest.ini` sets `pythonpath = .` and asyncio auto mode.

## Code Style

- Respect `.pre-commit-config.yaml`; hooks include ruff, black, codespell, JSON checks, yamllint, and prettier.
- Ruff line length is enforced at 88 chars by the pre-commit hook.
- Keep integration code under `custom_components/epex_spot_sensor/` and matching tests under `tests/`.
- Prefer small, focused changes. Do not reformat unrelated files unless a quality gate does it.

## Boundaries

ALWAYS:

- Use absolute paths in user-facing references.
- Run `.venv/bin/python -m pytest` before claiming test success.
- Run `pre-commit run --all-files` before commit-ready handoff.
- Quote exact errors when reporting failures.

ASK FIRST:

- Deleting, moving, or replacing files.
- Changing vendored code under `custom_components/epex_spot/`.
- Changing release, HACS, or Home Assistant manifest metadata.

NEVER:

- Commit secrets, tokens, local Home Assistant data, or personal configuration.
- Bypass or disable pre-commit hooks to make a change pass.
- Use Python 3.14 for the pinned test environment unless dependencies have been updated and verified.
