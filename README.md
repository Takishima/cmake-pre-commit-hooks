# pre-commit hooks

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/cmake-pre-commit-hooks?label=Python) [![PyPI version](https://badge.fury.io/py/cmake-pre-commit-hooks.svg)](https://badge.fury.io/py/cmake-pre-commit-hooks) [![CI Build](https://github.com/Takishima/cmake-pre-commit-hooks/actions/workflows/ci.yml/badge.svg)](https://github.com/Takishima/cmake-pre-commit-hooks/actions/workflows/ci.yml) [![CodeQL](https://github.com/Takishima/cmake-pre-commit-hooks/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/Takishima/cmake-pre-commit-hooks/actions/workflows/codeql-analysis.yml) [![pre-commit.ci status](https://results.pre-commit.ci/badge/github/Takishima/cmake-pre-commit-hooks/main.svg)](https://results.pre-commit.ci/latest/github/Takishima/cmake-pre-commit-hooks/main) [![CodeFactor](https://www.codefactor.io/repository/github/takishima/cmake-pre-commit-hooks/badge)](https://www.codefactor.io/repository/github/takishima/cmake-pre-commit-hooks) [![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=Takishima_cmake-pre-commit-hooks\&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=Takishima_cmake-pre-commit-hooks)[![Codacy Badge](https://api.codacy.com/project/badge/Grade/a3a1139e4bed4d4694bb12991b7df775)](https://app.codacy.com/gh/Takishima/cmake-pre-commit-hooks?utm_source=github.com\&utm_medium=referral\&utm_content=Takishima/cmake-pre-commit-hooks\&utm_campaign=Badge_Grade)

This is a [pre-commit](https://pre-commit.com) hooks repo that integrates C/C++ linters/formatters to work with
CMake-based projects.

> [clang-format](https://clang.llvm.org/docs/ClangFormatStyleOptions.html),
> [clang-tidy](https://clang.llvm.org/extra/clang-tidy/),
> [cppcheck](http://cppcheck.sourceforge.net/),
> [cpplint](https://github.com/cpplint/cpplint),
> [lizard](http://www.lizard.ws) and
> [iwyu](https://include-what-you-use.org/)

It is largely based on the work found [here](https://github.com/pocc/pre-commit-hooks). The main difference with POCC's
pre-commit hooks is that the ones from this repository will do a CMake configuration step prior to running any
pre-commit hooks. This is done in order to have CMake generate the compilation database file that can then be used by
the various hooks (using the `-DCMAKE_EXPORT_COMPILE_COMMANDS=ON` CMake option).

This repository is only has Python-based pre-commit hooks.

## Current known issues

1.  Currently, the hooks that depend on having a compilation database generated by CMake (e.g. `clang-tidy`, `cppcheck`)
    are not working on Windows if you are not using the `Ninja` or `Makefile` generators.

2.  Currently, arguments set in a TOML configuration file (`pyproject.toml`, `cmake_pc_hooks.toml` or else) are applied
    to all hooks. Future improvements may allow to customize arguments on a per-hook basis.

## Example usage

Assuming that you have the following directory structure for your projects

```text
root
├── .pre-commit-config.yaml
├── CMakeLists.txt
└── src
    └── err.cpp
```

with the following file contents:

**.pre-commit-config.yaml**

```yaml
repos:
  - repo: https://github.com/Takishima/cmake-pre-commit-hooks
    rev: v1.8.0
    hooks:
      - id: clang-format
      - id: clang-tidy
        args: [--checks=readability-magic-numbers,--warnings-as-errors=*]
      - id: cppcheck
      - id: include-what-you-use
```

**CMakeLists.txt**

```cmake
cmake_minimum_required(VERSION 3.15)
project(LANGUAGE CXX)
add_library(mylib STATIC src/err.cpp)
```

**src/err.cpp**

```cpp
#include <string>
int main() { int i; return 10; }
```

Running pre-commit on the above project will lead to an output similar to this one:

```text
$ pre-commit run --all-files
clang-format.............................................................Failed
- hook id: clang-format
- exit code: 1

src/err.cpp
====================
<  int main() { int i; return 10; }
---
>  int main() {
>    int i;
>    return 10;
>  }

clang-tidy...............................................................Failed
- hook id: clang-tidy
- exit code: 1

/tmp/temp/src/err.cpp:2:28: error: 10 is a magic number; consider replacing it with a named constant [readability-magic-numbers,-warnings-as-errors]
int main() { int i; return 10; }
                           ^

cppcheck.................................................................Failed
- hook id: cppcheck
- exit code: 1

/tmp/temp/src/err.cpp:2:18: style: Unused variable: i [unusedVariable]
int main() { int i; return 10; }
                 ^
include-what-you-use.....................................................Failed
- hook id: include-what-you-use
- exit code: 1

Problem with /usr/local/bin/iwyu_tool.py: Include-What-You-Use violations found

/tmp/temp/src/err.cpp should add these lines:
/tmp/temp/src/err.cpp should remove these lines:
- #include <string>  // lines 1-1
The full include-list for /tmp/temp/src/err.cpp:
---
```

Note that your mileage may vary depending on the version of the tools. The example above was generated using
`clang-format` 12.0.0, `clang-tidy` 12.0.0, `cppcheck` 2.4.1 and `include-what-you-use` 0.16.

## Using the Hooks

Python 3.8+ is required to use these hooks as all 3 invoking scripts are written in it. As this is also the minimum
version of pre-commit, this should not be an issue.

Running multiple hooks in parallel is currently supported by using the `fastener` Python package. If the hooks are run
in parallel, only one of the hooks will run the CMake configure step while the others will simply wait until the call to
CMake ends to continue. In the case where the hooks are run serially, all the hooks will be running the CMake configure
step. However, if nothing changed in your CMake configuration, this should not cost too much time.

### Installation

For installing the various utilities, refer to your package manager documentation. Some guidance can also be found
[here](https://github.com/pocc/pre-commit-hooks#installation).

### Hook Info

| Hook Info                | Type                     | Languages        |
|--------------------------|--------------------------|------------------|
| [clang-format][]         | Formatter                | C, C++, ObjC     |
| [clang-tidy][]           | Static code analyzer     | C, C++, ObjC     |
| [cppcheck][]             | Static code analyzer     | C, C++           |
| [cpplint][]              | Static code analyzer     | C, C++           |
| [include-what-you-use][] | Static code analyzer     | C, C++           |
| [lizard][]               | Code complexity analyzer | C/C++, ObjC, ... |

[clang-format]: https://clang.llvm.org/docs/ClangFormatStyleOptions.html

[clang-tidy]: https://clang.llvm.org/extra/clang-tidy/

[cppcheck]: http://cppcheck.sourceforge.net/

[cpplint]: https://github.com/cpplint/cpplint

[include-what-you-use]: https://include-what-you-use.org/

[lizard]: http://www.lizard.ws

### Hook options

Since v1.1.0 all hooks that depend on a compilation database (e.g. `clang-tidy`, `cppcheck`, `include-what-you-use`)
will attempt to generate a CMake build directory before running the actual command.

These hooks accept all the most common CMake options:

| CMake options                | Description                                      |
|------------------------------|--------------------------------------------------|
| `-S <path-to-source>`        | Explicitly specify a source directory.           |
| `-B <path-to-build>`         | Explicitly specify a build directory.            |
| `-D <var>[:<type>]=<value>`  | Create or update a cmake cache entry.            |
| `-U <globbing_expr>`         | Remove matching entries from CMake cache.        |
| `-G <generator-name>`        | Specify a build system generator.                |
| `-T <toolset-name>`          | Specify toolset name if supported by generator.  |
| `-A <platform-name>`         | Specify platform name if supported by generator. |
| `--preset <preset>`          | Specify a configure preset.                      |
| `-Wdev`                      | Enable developer warnings.                       |
| `-Wno-dev`                   | Suppress developer warnings.                     |
| `-Werror=dev`                | Make developer warnings errors.                  |
| `-Wno-error=dev`             | Make developer warnings not errors.              |

One important thing to note (particularly for those that intend to use this on CIs), you may specify the build directory
argument (`-B`) multiple times. The hooks will then simply cycle through all of the values provided and choose the first
directory that contains a configured CMake project (by looking at the presence of the `CMakeCache.txt` file). This may
be useful if you already have a build directory available somewhere that you would like to re-use. In the case where
none of the provided options is viable, the first one will automatically be selected as the build directory.

In addition to the above CMake options, the hooks also accept the following:

| Other hook options           | Description                                            | Note         |
|------------------------------|--------------------------------------------------------|--------------|
| `--all-at-once`              | Pass all filenames to the command at once              | Since v1.4.0 |
| `--clean`                    | Perform a clean CMake build                            | Since v1.4.0 |
| `--cmake`                    | Specify path to CMake executable                       | Since v1.4.0 |
| `--detect-configured-files`  | Enable cmake tracing and detection of configured files | Since v1.9.0 |
| `--dump-toml`                | Dump the current configuration as TOML on stdout       | Since v1.9.0 |
| `--no-automatic-discovery`   | Disable automatic build directory discovery            | Since v1.9.0 |
| `--read-json-db`             | Append file list from compile database                 | Since v1.7.0 |
| `--linux`                    | Linux-only CMake options                               | Since v1.3.0 |
| `--mac`                      | MacOS-only CMake options                               | Since v1.3.0 |
| `--win`                      | Windows-only CMake options                             | Since v1.3.0 |

NB: by specifying `--all-at-once` the linter/formatter command will only be called once for all the files instead of
calling the command once per file.

NB: Since v1.6.0, the `--debug` command line argument has been removed. Use the `LOGLEVEL` environment variable instead
to control the level of verbosity of each of the commands. To show all debug messages, set `LOGLEVEL=DEBUG` in your
environment variables when running the hooks.

NB: by specifying `--read-json-db` the hook will read the list of files from the `compile_commands.json` generated by
CMake and will append those files to the list of files to process regardless of the list of files otherwise passed on
the command line.

Usage example:

```yaml
repos:
- repo: https://github.com/Takishima/cmake-pre-commit-hooks
  rev: v1.8.0
  hooks:
    - id: cppcheck
      args: [-DBUILD_TESTING=ON,
             --unix="-DCMAKE_CXX_COMPILER=g++-10",
             --win="-DCMAKE_CXX_COMPILER=cl.exe"
             -Bpath/to/build_dir,
             -Bpath/to/other_build_dir,
             -Spath/to/src_dir
             ]
```

In the example above, the any hooks requiring a compilation database will first search for a build directory
`path/to/build_dir` and then `path/to/other_build_dir`. If any of those is deemed valid (ie. is a CMake build directory
that contains some CMake cache files), then it will be used. If none qualify, the hooks will default to using
`path/to/build_dir` as a build directory, creating it as necessary.

Also, builds on Linux and MacOS will set the C++ compiler to `g++-10`, while builds on Windows will be using
`cl.exe`. This is done by looking at the value returned by
[`platform.system()`](https://docs.python.org/3/library/platform.html#platform.system).

### TOML support

Since v1.9.0, the hooks support loading the CLI arguments from TOML files. This can be used to configure all the hooks
for a particular repository using either of:

1.  `pyproject.toml`
2.  `cmake_pc_hooks.toml`
3.  TOML file specified using `--config=/path/to/file.toml`
4.  Command line arguments

Note that each step in the above list is overridden by the steps that happen **after** it. For example, CLI arguments
will always override any arguments read from any TOML file.

A good place to start if you plan on creating a TOML configuration file is to use the hooks using the CLI arguments as
you would normally and then run the hook manually and with the addition of `--dump-toml`. This will output a
TOML-formatted configuration on the standard output for all the parameters that *diverge* from their default values.

For example, running the following command (assuming that no valid TOML configuration exists):

```bash
cmake-pc-clang-format-hook tests/cmake_bad/bad.cpp  --dump-toml -B /tmp/build -S source -Wdev --no-automatic-discovery
```

will result in the following output:

```toml
automatic_discovery = false
source_dir = "source"
build_dir = [ "/tmp/build",]
dev_warnings = true
```

### CMake configured file detection

Since v1.9.0, the hooks support the use of CMake with trace mode enabled in order to keep track of files that are
generated using calls to the `configure_file(...)` CMake function. If `--detect-configured-files` is specified on the command line
(or in some TOML configuration file), the hooks will attempt to locate those generated files and automatically add them
to the list of processed files for any hook invocation.

### Hook Option Comparison

| Hook Options             | Fix In Place        | Enable all Checks                        | Set key/value |
|--------------------------|---------------------|------------------------------------------|---------------|
| [clang-format][]         | `-i`                |                                          |               |
| [clang-tidy][]           | `--fix-errors` [^1] | `-checks=*` `-warnings-as-errors=*` [^2] |               |
| [cppcheck][]             |                     | `-enable=all`                            |               |
| [include-what-you-use][] |                     |                                          |               |

[^1]: `-fix` will fail if there are compiler errors. `-fix-errors` will `-fix` and fix compiler errors if it can, like missing semicolons.

[^2]: Be careful with `-checks=*`; some checks can have self-contradictory rules in newer versions of LLVM (9+). For
    example, modernize wants to use [trailing return type][] but Fuchsia [disallows it][].

[trailing return type]: https://clang.llvm.org/extra/clang-tidy/checks/modernize-use-trailing-return-type.html

[disallows it]: https://clang.llvm.org/extra/clang-tidy/checks/fuchsia-trailing-return.html

### The '--' doubledash option

Options after `--` like `-std=c++11` will be interpreted correctly for `clang-tidy`. Make sure they sequentially follow
the `--` argument in the hook's args list.

### Standalone Hooks

If you want to have predictable return codes for your C linters outside of pre-commit, these hooks are available via
[PyPI](https://pypi.org/project/cmake-pre-commit-hooks/).  Install it with `pip install cmake-pre-commit-hooks`.  They
are named as `cmake-pc-$cmd-hook`, so `clang-format` becomes `cmake-pc-clang-format-hook`.
