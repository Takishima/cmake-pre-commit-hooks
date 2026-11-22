# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Changes that are not released yet are stored as fragments in the [changelog.d](changelog.d/README.md) directory.

<!-- towncrier release notes start -->

## [v2.0.0](https://github.com/Takishima/cmake-pre-commit-hooks/releases/tag/v2.0.0) - 2026-11-22

### Breaking changes

- Rename the version check from `--version` to `--require-version`; the hook now runs the tool after a successful check, and `--version` shows the version of the hooks ([#163](https://github.com/Takishima/cmake-pre-commit-hooks/issues/163))
- Make all hooks fail when there is no file to process (unless `--all-at-once` is used), as the hooks using CMake already did
- Rename the option to specify a TOML file from `--config` to `--hooks-config`; `--config` is now passed on to the underlying tool
- Select the files of the `clang-format`, `clang-tidy`, `cpplint` and `include-what-you-use` hooks with `types_or` instead of a list of extensions: more C/C++ extensions are now matched (e.g. `.hh`, `.inl`, `.ipp`, `.tpp`, `.mm`) but `.mxx` files no longer are, unless `types_or` and `files` are overridden in the configuration of the hook

### Added

- Support settings for a single hook in TOML files, in a table named after the hook (e.g. `[tool.cmake_pc_hooks.clang-tidy]`)
- Support the common hook options and the TOML configuration in the `cpplint` hook, which now also reports the errors of all the files instead of stopping at the first failing one

### Changed

- Parse the command line with `click` and read TOML files with the standard library, removing the `toml` dependency ([#160](https://github.com/Takishima/cmake-pre-commit-hooks/issues/160))
- Declare `minimum_pre_commit_version: 3.2.0` for all the hooks, so that older versions of pre-commit fail with a clear message
- Only look for and set up CMake when a hook needs it, which also makes `--read-json-db` work with the `clang-format` hook
- Print the output of a tool as soon as each file is processed instead of at the end, and always exit with code 1 on failure
- Remove the dependency on the `CLinters` package by implementing the base classes of the hooks in this package
- Report a clear error instead of a traceback when the tool of a hook is not installed

### Fixed

- Fix the hooks passing a compilation database that does not exist to the tool when `--no-cmake-configure` is used, and look for one in the other build directories ([#154](https://github.com/Takishima/cmake-pre-commit-hooks/issues/154))
- Fix `-S` accepting a path that is not a directory, and check it for all hooks
- Fix a TOML file passed on the command line not overriding the settings of `pyproject.toml` and `cmake_pc_hooks.toml`
- Fix clang-format hook failing on empty files
- Fix the `unix` setting having no effect when set in a TOML file

### Repository

- Split the CMake code into a package of focused modules with a typed options object ([#150](https://github.com/Takishima/cmake-pre-commit-hooks/issues/150))
- Retry failed integration tests once on Windows with Python 3.10, which sometimes crashes at exit ([#156](https://github.com/Takishima/cmake-pre-commit-hooks/issues/156))
- Fix the name of the package directory in `MANIFEST.in` ([#157](https://github.com/Takishima/cmake-pre-commit-hooks/issues/157))
- Add a `breaking` changelog fragment type, which makes the release workflow propose a major version
- Exclude the changelog fragments from the Codacy analysis
- Fix the minimum Python version stated in the README (3.10, not 3.8)
- Make the pre-commit.ci settings explicit, add the `check-hooks-apply` meta hook and remove the `check-symlinks` and `shellcheck` hooks that it reports as not matching any file
- Run all hooks through one shared runner, with each hook reduced to a short description of its tool

## [v1.10.0](https://github.com/Takishima/cmake-pre-commit-hooks/releases/tag/v1.10.0) - 2026-11-22

### Added

- Added `--codegen` option to build the `codegen` target provided by CMake 3.31+. The hooks check that the CMake version and generator support that target before attempting to build it. ([#105](https://github.com/Takishima/cmake-pre-commit-hooks/issues/105))
- Added `--cmake-build-target` option to build some CMake targets after the CMake configure step (e.g. to generate source files before running the hooks)
- The hooks now install CMake (>= 3.31) from PyPI if no CMake executable can be found on the system at installation time. A system CMake is still preferred if present.

### Changed

- Add support for Python 3.13, 3.14 and 3.15
- Drop support for Python 3.8 and 3.9 (end-of-life); the minimum required Python version is now 3.10
- Remove the dependency on `filelock`

### Fixed

- Build Python 3 only wheels (`py3-none-any`) instead of universal `py2.py3` ones
- Fixed PowerShell system test script using `$?` instead of `$LASTEXITCODE` for exit code handling
- Fixed `--clean` being silently ignored by all the hooks
- Fixed `--version` always failing for the include-what-you-use hook
- Fixed `-Wno-dev` being passed to CMake as `-Wno_dev`, which is rejected by recent versions of CMake
- Fixed hooks running concurrently on the same build directory sometimes not waiting for the CMake configure step of another hook to complete
- Fixed include-what-you-use hook passing when the output for a correct file is mixed with the output for an incorrect one (e.g. when using `--all-at-once`)
- Fixed lizard hook only considering the exit code of the last file when processing more than one file

### Repository

- Add `AGENTS.md` and `CLAUDE.md` with instructions for AI coding tools
- Allow uploading to PyPI using trusted publishing
- Build the release from the merged commit using `SETUPTOOLS_SCM_PRETEND_VERSION` instead of a temporary Git tag
- Cancel superseded workflow runs on pull requests and restrict default workflow token permissions
- Check that pull requests add a changelog fragment and do not edit `CHANGELOG.md` directly (replaces the `dangoslen/changelog-enforcer` GitHub Action)
- Clarify where to put the settings in `pyproject.toml`
- Cleanup of the linter pragmas in the code: remove obsolete `# pylint: disable` comments, replace repeated inline `ruff` suppressions with entries in the `ruff` configuration in `pyproject.toml` and merge nested `with` statements in `_cmake.py`
- Cleanup of the pre-commit configuration: remove the `doc8` hook (there are no reStructuredText files in the repository), remove the unused `ruff` dependency of the `blacken-docs` hook and run the `ruff` linter (with fixes) before the `ruff` formatter
- Deduce the next version from the changelog fragments when drafting a release (`auto`, `patch`, `minor`, `major` or an explicit, validated version), using a tested script in `.github/scripts/`
- Delete the release branch once the release is published
- Exclude the release automation scripts from the SonarCloud coverage and grant the `pull-requests: read` permission at job level
- Fix SonarCloud violations (return type annotation of `_load_from_toml`, cognitive complexity of `_cmake.py` and `_cmake_test.py`, variable naming in the tests, user-controlled data and unvalidated `workflow_dispatch` inputs in the GitHub workflows, shell script issues in `run_tests.sh`)
- Fix the pre-release detection when creating the GitHub release
- Fixed Windows CI by using pip to install cppcheck (Chocolatey package is broken)
- Generate the changelog fragments of pre-commit.ci pull requests with a script from this repository, also when pre-commit.ci updates its pull request
- Group all Dependabot GitHub Actions updates (now including `actions/*`) into a single pull request; these pull requests do not need a changelog entry
- Ignore SonarCloud rules about missing lock files and unpinned `pip install` in CI (not applicable to a library)
- Make the `Finish CI checks` job fail instead of being skipped when one of its dependencies fails
- Manage the CHANGELOG with [towncrier](https://towncrier.readthedocs.io): each pull request adds a fragment to `changelog.d/` and the fragments are collected into `CHANGELOG.md` when a release is drafted
- Modernize ruff configuration to follow latest guidelines: remove deprecated settings (`target-version`, `ANN101`, `ASYNC1`, etc.), replace `TCH` with `TC` (renamed rule set) and add the `DOC`, `PYI` and `PD` rule sets
- Open the release pull request automatically every Monday if user-facing changes are waiting to be released
- Reference GitHub Actions by their major version tag instead of a full commit SHA and ignore the corresponding SonarCloud rule
- Rewrite the system tests (`tests/run_tests.sh` and `tests/run_tests.ps1`) as a cross-platform pytest test suite (`tests/integration`) that runs in parallel on temporary copies of the test projects, checks the output of the hooks and not only their exit code, and also covers most of the CMake related options, TOML configuration files, concurrent execution of the hooks and changes that are not yet committed
- Skip the SonarCloud and Codacy coverage uploads when secrets are not available (Dependabot and fork pull requests) instead of failing
- Split the release publishing workflow into separate build, PyPI upload and GitHub release jobs with minimal permissions; the GitHub release is only created once the PyPI upload succeeded
- Update GitHub Action `EndBug/add-and-commit` from v9 to v11
- Update GitHub Action `SonarSource/sonarqube-scan-action` to v8
- Update GitHub Action `actions/checkout` from v4 to v7
- Update GitHub Action `actions/download-artifact` from v4 to v8
- Update GitHub Action `actions/setup-python` from v5 to v7
- Update GitHub Action `actions/upload-artifact` from v4 to v7
- Update GitHub Action `codecov/codecov-action` from v4 to v7
- Update GitHub Action `github/codeql-action` from v3 to v4
- Update `Lucas-C/pre-commit-hooks` hook to v1.5.6
- Update `adrienverge/yamllint` hook to v1.38.0
- Update `asottile/blacken-docs` hook to v1.20.0
- Update `astral-sh/ruff-pre-commit` hook to v0.17.5 and convert `# noqa` comments to the new `# ruff: ignore[...]` syntax
- Update `codespell-project/codespell` hook to v2.4.3
- Update `pre-commit/pre-commit-hooks` hook to v6.0.0
- Update `shellcheck-py/shellcheck-py` hook to v0.11.0.1-1
- Use the `peter-evans/create-pull-request`, `softprops/action-gh-release` and `taiki-e/install-action` GitHub Actions in the release workflows (replacing `stefanzweifel/git-auto-commit-action`, `thomaseizinger/create-pull-request` and hand-written shell code)

## [v1.9.6] - 2024-06-02

### Changed

- Apply new linter/formatters

### Fixed

- Fixed a bug where a condition always evaluated to `true`

### Repository

- Update GitHub Action `action/setup-python` to v5
- Update GitHub Action `codecov/codecov-action` from v3 to v4
- Update GitHub Action `ilammy/msvc-dev-cmd` from v1.12.1 to v1.13.0
- Update GitHub Action `thomaseizinger/create-pull-request` to v1.4.0
- Update `adrienverge/yamllint` hook to v1.35.1
- Update `astral-sh/ruff-pre-commit` hook to v0.4.5
- Update `codespell-project/codespell` hook to v2.3.0
- Update `Lucas-C/pre-commit-hook` hook to v1.5.5
- Update `pre-commit/pre-commit-hooks` hook to v4.6.0
- Update `shellcheck-py/shellcheck-py` hook to v0.10.0

## [v1.9.5] - 2023-12-15

### Added

- Added metadata to mark support for Python 3.12 and enabled CI checks for it
- Implemented PEP-621

### Changed

- Remove all Python linters/formatters in favour of ruff
- Require setuptools>=61.0 in preparation for PEP-621

### Repository

- Fix GitHub workflows
- Update `astral-sh/ruff-pre-commit` to v0.1.8
- Update `adrienverge/yamllint` hook to v1.33.0

## [v1.9.4] - 2023-10-15

### Added

- Added dependency on the Python `attrs` library

### Changed

- Improved the printing of output when multiple files have been processed

### Repository

- Update `pre-commit/pre-commit-hooks` hook to v4.5.0

## [v1.9.3] - 2023-10-09

### Fixed

- Fixed an issue when handling `--` arguments

### Repository

- Update `asottile/blacken-docs` hook to v1.16.0
- Update `astral-sh/ruff-pre-commit` to v0.0.292
- Update `codespell-project/codespell` hook to v2.2.6
- Update `Lucas-C/pre-commit-hooks` hook to v1.5.4
- Update `psf/black` hook to v23.9.1
- Update `shellcheck-py/shellcheck-py` hook to v0.9.0.6
- Update GitHub Action `stefanzweifel/git-auto-commit-action` to v5

## [v1.9.2] - 2023-07-19

### Added

- Added `--no-cmake-configure` option to avoid calling CMake configure but still use a compilation database if one can
  be found

### Repository

- Update `asottile/blacken-docs` hook to v1.15.0
- Update `astral-sh/ruff-pre-commit` to v0.0.278
- Update `charliermarsh/ruff-pre-commit` hook to v0.0.275
- Update `codespell-project/codespell` hook to v2.2.5
- Update `psf/black` hook to v23.7.0
- Upgrade GitHub Action `thomaseizinger/create-pull-request` to v1.3.1

## [v1.9.1] - 2023-06-18

### Changed

- Add proper support for clang-format "linter" mode (ie. `--dry-run`)

### Fixed

- Avoid setting up CMake arguments for clang-format hook

### Repository

- Update release drafting GitHub workflow
- Modify pull requests workflow to automatically update CHANGELOG file if it was created by pre-commit.ci
- Update `charliermarsh/ruff-pre-commit` hook to v0.0.272
- Update `shellcheck-py/shellcheck-py` hook to v0.9.0.5

## [v1.9.0] - 2023-05-24

### Added

- Added Python tests using PyTest
- Added support for parsing hook parameters from TOML configuration files
- Added option to dump the current configuration as TOML-formatted output on the standard output (`--dump-toml`)
- Added option to parse CMake trace output to detect files generated using `configure_file(...)`

### Fixed

- Fixed potential issue with CppCheck hook always running on all files in compile database

### Changed

- CppCheck hook will now exclude C++ header files by default since those are not present within the compilatioon databasebecauzse
- Make default logging level `INFO` instead of `WARNING`
- Move all CMake handling code into dedicated sub-module
- Minor adjustments to logging output format
- Update README

### Repository

- Use [ruff](https://beta.ruff.rs/docs/) for linting over other Python linters
- System tests now run using LOGLEVEL=DEBUG
- Improved configuration for external linters (e.g. SonarCloud, Codacy)
- Update `yamllint` hook to v1.32.0

## [v1.8.1] - 2023-04-20

### Added

- Added support for C++ module files by default

### Fixed

- Fixed some typos in the README file (thanks to @onuralpszr)

### Changed

- Require users to explicitly set `-B`|`--build-dir` if they pass `--preset` to CMake (see issue [#63](https://github.com/Takishima/cmake-pre-commit-hooks/issues/63))

### Repository

- Update `Lucas-C/pre-commit-hooks` hook to v1.5.1
- Update `codespell` to v2.2.4
- Update `yamllint` hook to v1.30.0
- Update `black` hook to v23.3.0
- Update `bandit` hook to v1.7.5
- Update `isort` hook to v5.12.0

## [v1.8.0] - 2023-02-16

### Added

- Added support for the CMake `--preset` command line argument

## [v1.7.0] - 2023-02-09

### Added

- Added support for reading `compile_commands.json` (generated by CMake) when running the hooks in order to
  automatically discover files

### Updated

- Added some more pre-commit hooks:
  - shellcheck
  - bandit

### Repository

- Add new badges to README file for CodeFactor.io and SonarCloud
- Update `black` hook to v23.1.0

## [v1.6.0] - 2023-02-07

### Added

- Added `include-what-you-use-conda` and `cppcheck-conda` hooks to install both tools using conda environments

### Changed

- Changed minimum Python version to 3.8.X
- Allow `lizard` hook to handle Fortran files

### Updated

- Update GitHub release publishing workflow
- Added some more pre-commit hooks:
  - doc8
  - codespell
  - yamllint
  - blacken-docs
  - pyupgrade

### Repository

- Update `action/setup-python` GitHub Action to v5
- Update `action/checkout` GitHub Action to v4
- Update `github/codeql-action/analyze` GitHub Action to v3
- Update `ilammy/msvc-dev-cmd` GitHub Action to v1.12.1
- Update `thomaseizinger/create-pull-request` GitHub Action to v1.3.0
- Update `Lucas-C/pre-commit-hooks` hook to v1.4.2
- Update `asottile/pyupgrade` to v3.2.0
- Update `black` hook to v22.10.0
- Update `blacken-docs` hook to v1.13.0
- Update `flake8` hook to v5.0.4
- Update `pre-commit/mirrors-pylint` to v3.0.0a5
- Update `pre-commit/pre-commit-hooks` to v4.3.0
- Update `pyupgrade` hook to v3.3.1
- Update `yamllint` hook to v1.29.0
- Update `isort` hook to v5.12.0

## [v1.5.3] - 2022-06-14

### Added

- Add support for installing `clang-format` using Python if not found on the system
- Add support for installing `lizard` automatically if not found on the system

### Fixed

- Correctly pass on the default argument list to `CLinters`
- Fixed issues with release publishing workflows on GitHub

### Repository

- Update GitHub's CodeQL action to v2
- Update `astral-sh/ruff-pre-commit` hook to v0.4.7
- Update `pre-commit/pre-commit-hooks` hook to v4.3.0
- Update `Lucas-C/pre-commit-hooks` hook to v1.2.0
- Update `pre-commit/mirrors-pylint` hook to v3.0.0a5
- Update `dangoslen/changelog-enforcer` GitHub action to v3
- Update `thomaseizinger/create-pull-request` GitHub action to v1.2.2
- Update `black` hook to v22.3.0
- Update `check-manifest` to v0.48

## [v1.5.2] - 2021-12-08

### Fixed

- Fixed indentation issue

## [v1.5.1] - 2021-12-08

### Fixed

- Fixed locating of compilation database in presence of a symbolic link in the source directory

### Repository

- New step in "Format" GitHub action to make sure the CHANGELOG is updated with proper version section for hotfix/\_
  and release/\_ branches
- Update `isort` hook to v5.10.1
- Update `black` hook to v21.12b0
- Disable macOS CI for Python < 3.11 (now runs on M1 macs on GitHub)

## [v1.5.0] - 2021-11-08

### Added

- Support for `cpplint`
- Support for `lizard`, a code complexity analyzer

### Repository

- Update pre-commit hooks
- Update `thomaseizinger/create-pull-request` GiHub action to v1.3.0
- Update `isort` hook to v5.10.0
- Update `black` hook to v21.10b0
- Update `check-manifest` hook to v0.47
- Update `flake8` hook to v4.0.1

## [v1.4.0] - 2021-07-16

### Added

- Support for simultaneous processing of all files using `--all-at-once`

### Updated

- Improved code handling standard output and error stream in case of multiple files
- Minor improvements to debugging output

### Fixed

- Do not attempt to copy the compilation database in the source directory if it exists and is a symbolic link
- Properly handle the `--cmake` command line option

### Repository

- Cleanup of `pre-commit-config.yaml` and added
- Added some more flake8 plugins to the list used by `pre-commit`:
  - flake8-breakpoint
  - flake8-comprehensions
  - flake8-docstrings
  - flake8-eradicate
  - flake8-mutable

## [v1.3.0] - 2021-06-27

### Added

- Support for platform-specific CMake options
  Use `--linux`, `--mac` and `--win` to specify CMake flags that need to be provided only on the specific
  platform. `--unix` can be used as a shortcut to specifying `--linux` and `--mac`.

## [v1.2.0] - 2021-06-27

### Added

- Support for Include-What-You-Use

### Fixed

- Double-dash arguments not present in debug output

### Repository

- Add tests that use pre-commit directly
- Add isort pre-commit hook

## [v1.1.2] - 2021-06-26

### Added

- Added debug command line option to show the exact commands being run when using pre-commit regardless of exit status

### Fixed

- Properly handle double-dash arguments for clang-tidy when multiple files are passed to the hook

## [v1.1.1] - 2021-06-26

### Updated

- Added support for CUDA files by default

### Fixed

- Default source directory is now correctly set to the current directory

### Repository

- Fix automatic release publication workflow

## [v1.1.0] - 2021-06-22

### Updated

- Added Python 3.9 in the package's metadata
- Support for specifying more than one build directory
  If one of those exists and contains a configured CMake directory, that one will be chosen. If none already exist,
  the first specified alternative will be chosen.

### Fixed

- Issues with arguments parsing for arguments that are specified more than once
- Fix issue with CMake configure step when running hooks in parallel

### Repository

- Update pre-commit configuration

## [v1.0.1] - 2021-06-20

### Added

- Support for GitHub actions
- Small test scripts for Linux, MacOS and Windows (only partial testing)

### Updated

- Slightly more verbose output on certain failures

### Fixed

- Issue when passing paths to `subprocess.run()` on Windows
- CMake arguments being parsed more than once

## [v1.0.0] - 2021-06-18

Initial release with support for:

- clang-format
- clang-tidy
- cppcheck

[v1.0.0]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/20b1113bf223273cda31a14a82c9d573a342de4a...v1.0.0
[v1.0.1]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.0.0...v1.0.1
[v1.1.0]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.0.1...v1.1.0
[v1.1.1]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.1.0...v1.1.1
[v1.1.2]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.1.1...v1.1.2
[v1.2.0]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.1.2...v1.2.0
[v1.3.0]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.2.0...v1.3.0
[v1.4.0]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.3.0...v1.4.0
[v1.5.0]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.4.0...v1.5.0
[v1.5.1]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.5.0...v1.5.1
[v1.5.2]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.5.1...v1.5.2
[v1.5.3]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.5.2...v1.5.3
[v1.6.0]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.5.3...v1.6.0
[v1.7.0]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.6.0...v1.7.0
[v1.8.0]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.7.0...v1.8.0
[v1.8.1]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.8.0...v1.8.1
[v1.9.0]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.8.1...v1.9.0
[v1.9.1]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.9.0...v1.9.1
[v1.9.2]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.9.1...v1.9.2
[v1.9.3]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.9.2...v1.9.3
[v1.9.4]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.9.3...v1.9.4
[v1.9.5]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.9.4...v1.9.5
[v1.9.6]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.9.5...v1.9.6
