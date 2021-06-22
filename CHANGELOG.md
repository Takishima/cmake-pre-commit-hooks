# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Updated

- Added Python 3.9 in the package's metadata
- Support for specifying more than one build direcory
  If one of those exists and contains a configured CMake directory, that one will be chosen. If none already exist, the
  first specified alternative will be chosen.

### Fixed

- Issues with arguments parsing for arguments that are specified more than once

### Repository

- Update pre-commit configuration

## [1.0.1] - 2021-06-20

### Added

- Support for GitHub actions
- Small test scripts for Linux, MacOS and Windows (only partial testing)

### Updated

- Slightly more verbose output on certain failures

### Fixed

- Issue when passing paths to `subprocess.run()` on Windows
- CMake arguments being parsed more than once

## [1.0.0] - 2021-06-18

Initial release with support for:
- clang-format
- clang-tidy
- cppcheck
