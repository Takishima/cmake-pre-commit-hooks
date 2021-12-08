# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]


## [1.5.1] - 2021-12-08

### Fixed

-   Fixed locating of compilation database in presence of a symbolic link in the source directory

### Repository

-   New step in "Format" GitHub action to make sure the CHANGELOG is updated with proper version section for hotfix/*
    and release/* branches
-   Update `isort` hook to v5.10.1
-   Update `black` hook to v21.12b0

## [1.5.0] - 2021-11-08

### Added

-   Support for `cpplint`
-   Support for `lizard`, a code complexity analyzer

### Repository

-   Update pre-commit hooks
-   Update `thomaseizinger/create-pull-request` GiHub action to v1.3.0
-   Update `isort` hook to v5.10.0
-   Update `black` hook to v21.10b0
-   Update `check-manifest` hook to v0.47
-   Update `flake8` hook to v4.0.1

## [1.4.0] - 2021-07-16

### Added

-   Support for simultaneous processing of all files using `--all-at-once`

### Updated

-   Improved code handling standard output and error stream in case of multiple files
-   Minor improvements to debugging output

### Fixed

-   Do not attempt to copy the compilation database in the source directory if it exists and is a symbolic link
-   Properly handle the `--cmake` command line option

### Repository

-   Cleanup of `pre-commit-config.yaml` and added
-   Added some more flake8 plugins to the list used by `pre-commit`:
    -   flake8-breakpoint
    -   flake8-comprehensions
    -   flake8-docstrings
    -   flake8-eradicate
    -   flake8-mutable

## [1.3.0] - 2021-06-27

### Added

-   Support for platform-specific CMake options
    Use `--linux`, `--mac` and `--win` to specify CMake flags that need to be provided only on the specific
    platform. `--unix` can be used as a shortcut to specifying `--linux` and `--mac`.

## [1.2.0] - 2021-06-27

### Added

-   Support for Include-What-You-Use

### Fixed

-   Double-dash arguments not present in debug output

### Repository

-   Add tests that use pre-commit directly
-   Add isort pre-commit hook

## [1.1.2] - 2021-06-26

### Added

-   Added debug command line option to show the exact commands being run when using pre-commit regardless of exit status

### Fixed

-   Properly handle double-dash arguments for clang-tidy when multiple files are passed to the hook

## [1.1.1] - 2021-06-26

### Updated

-   Added support for CUDA files by default

### Fixed

-   Default source directory is now correctly set to the current directory

### Repository

-   Fix automatic release publication workflow

## [1.1.0] - 2021-06-22

### Updated

-   Added Python 3.9 in the package's metadata
-   Support for specifying more than one build direcory
    If one of those exists and contains a configured CMake directory, that one will be chosen. If none already exist,
    the first specified alternative will be chosen.

### Fixed

-   Issues with arguments parsing for arguments that are specified more than once

### Repository

-   Update pre-commit configuration

## [1.0.1] - 2021-06-20

### Added

-   Support for GitHub actions
-   Small test scripts for Linux, MacOS and Windows (only partial testing)

### Updated

-   Slightly more verbose output on certain failures

### Fixed

-   Issue when passing paths to `subprocess.run()` on Windows
-   CMake arguments being parsed more than once

## [1.0.0] - 2021-06-18

Initial release with support for:

-   clang-format
-   clang-tidy
-   cppcheck

[Unreleased]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.5.0...HEAD

[1.5.0]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.4.0...v1.5.0

[1.4.0]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.3.0...v1.4.0

[1.3.0]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.2.0...v1.3.0

[1.2.0]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.1.2...v1.2.0

[1.1.2]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.1.1...v1.1.2

[1.1.1]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.1.0...v1.1.1

[1.1.0]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.0.1...v1.1.0

[1.0.1]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/v1.0.0...v1.0.1

[1.0.0]: https://github.com/Takishima/cmake-pre-commit-hooks/compare/20b1113bf223273cda31a14a82c9d573a342de4a...v1.0.0
