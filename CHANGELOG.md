# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Repository

- Clarify where to put the settings in `pyproject.toml`

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
- Disable macOS CI for Python \< 3.11 (now runs on M1 macs on GitHub)

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

[unreleased]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.9.6...HEAD
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
