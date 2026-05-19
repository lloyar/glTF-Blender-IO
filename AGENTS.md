# Repository Guidelines

## Project Structure & Module Organization
Core addon code lives in `addons/io_scene_gltf2/`.
- `blender/`: Blender-facing importer/exporter logic (`exp/`, `imp/`, `com/`).
- `io/`: Blender-independent glTF model, serialization, and parsing (`io/exp`, `io/imp`, `io/com`).
- `__init__.py`: addon entrypoint and Blender operator registration.

Tests and fixtures are in `tests/`:
- `tests/test/test.js`: Mocha test runner and validator checks.
- `tests/scenes/`: source `.blend` scenes.
- `tests/roundtrip/`: expected glTF/GLB roundtrip artifacts.

Supporting docs/assets: `README.md`, `Technical.md`, `DEBUGGING.md`, `docs/`, `images/`, and helper scripts in `tools/`.

## Build, Test, and Development Commands
From repo root:
- `cd tests && yarn install`: install test dependencies.
- `cd tests && yarn test`: run full Mocha + glTF validator suite.
- `cd tests && yarn test-bail`: stop on first failing test.
- `cd tests && yarn lint` / `yarn lint:fix`: lint/fix JavaScript test code.

Prerequisite: `blender` must be on `PATH` (headless mode is used by tests).

## Coding Style & Naming Conventions
Python:
- 4-space indentation, max line length `120` (see `pyproject.toml`).
- Prefer `autopep8` settings from repo config; avoid large unrelated reformatting.
- Follow existing module naming (`gltf2_blender_*`, `gltf2_io_*`) and snake_case functions.

JavaScript tests:
- ESLint rules in `tests/.eslintrc.json` (2-space indent, semicolons expected).

## Testing Guidelines
Add or update tests for behavior changes in importer/exporter paths.
- Scene fixtures: `tests/scenes/NN_feature_name.blend`.
- Roundtrip fixtures: `tests/roundtrip/NN_feature_name/` with `.gltf/.bin` (and optional `*_options.txt`).

Run `cd tests && yarn test` before opening a PR. Prefer `yarn test-bail` during iteration.

## Commit & Pull Request Guidelines
Recent history favors short, imperative subjects with optional prefix, e.g.:
- `Fix crash when reloading scripts`
- `Add support for exporting node visibility animations`
- `Bump to 5.1.18`

PRs should include:
- Clear problem/solution summary and impacted importer/exporter paths.
- Linked issue(s) when applicable.
- Test evidence (commands run, relevant output).
- For bug fixes, attach reproducible sample assets (`.blend` / `.gltf` + textures) when possible.
