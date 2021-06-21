# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
