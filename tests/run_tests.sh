#! /bin/bash

set -x

build_dir=build

function run_hook()
{
    hook=$1
    src_dir=$2
    expect_success=$3
    gen_compiledb=$4
    shift 4

    mkdir -p $build_dir
    rm -rf $build_dir/*

    if [ $gen_compiledb -eq 1 ]; then
        $hook -S $src_dir -B $build_dir "$@"
    else
        $hook "$@"
    fi
    ret=$?

    if [ $expect_success -eq 1 ]; then
        if [ $ret -ne 0 ]; then
            echo "Hook $hook failed on source directory $src_dir with exit code $ret!"
            exit 1
        fi
    else
        if [ $ret -eq 0 ]; then
            echo "Hook $hook unexpectedly succeeded on source directory $src_dir with exit code $ret!"
            exit 1
        fi
    fi

    if [ $gen_compiledb -eq 1 ]; then
        if [ ! -f $build_dir/compile_commands.json ]; then
            echo "Hook $hook failed to generate the compile database for $src_dir!"
            exit 1
        fi
    fi
}

# ==============================================================================

run_hook cmake-pc-clang-format-hook tests/cmake_good 1 0 tests/cmake_good/good.cpp
run_hook cmake-pc-clang-tidy-hook tests/cmake_good 1 1 --checks=readability-magic-numbers --warnings-as-errors=* tests/cmake_good/good.cpp
run_hook cmake-pc-cppcheck-hook tests/cmake_good 1 1 tests/cmake_good/good.cpp
run_hook cmake-pc-cpplint-hook tests/cmake_good 1 0 tests/cmake_good/good.cpp
run_hook cmake-pc-include-what-you-use-hook tests/cmake_good 1 1 --debug tests/cmake_good/good.cpp
run_hook cmake-pc-lizard-hook tests/cmake_good 1 0 tests/cmake_good/good.cpp

# Test multiple build directory options
mkdir -p $build_dir
rm -rf $build_dir/*
cmake -B other_build -S tests/cmake_good
cmake-pc-cppcheck-hook -S tests/cmake_good -B build -B other_build tests/cmake_good/good.cpp
if [ ! -f other_build/compile_commands.json ]; then
    echo "Failed to generate compile database in other_build"
    exit 1
fi

# ------------------------------------------------------------------------------

run_hook cmake-pc-clang-format-hook tests/cmake_bad 0 0 tests/cmake_bad/bad.cpp
run_hook cmake-pc-clang-tidy-hook tests/cmake_bad 0 1 --checks=readability-magic-numbers --warnings-as-errors=* tests/cmake_bad/bad.cpp
run_hook cmake-pc-cppcheck-hook tests/cmake_bad 0 1 tests/cmake_bad/bad.cpp
run_hook cmake-pc-cpplint-hook tests/cmake_bad 0 0 tests/cmake_bad/bad.cpp
run_hook cmake-pc-include-what-you-use-hook tests/cmake_bad 0 1 --debug tests/cmake_bad/bad.cpp
run_hook cmake-pc-lizard-hook tests/cmake_bad 0 0 -C4 tests/cmake_bad/bad.cpp

# ==============================================================================

export CC=clang CXX=clang++


if [ -z "$GITHUB_SHA" ]; then
    LATEST_SHA=$(git rev-parse HEAD)
else
    LATEST_SHA=$GITHUB_SHA
fi

call_sed()
{
    if [[ "$OSTYPE" == "darwin"* ]]; then
        gsed "$@"
    else
        sed "$@"
    fi
}


pushd tests/cmake_good
git init \
    && git config user.name 'Test' \
    && git config user.email 'test@test.com' \
    && call_sed -i "/rev: /c\\    rev: ${LATEST_SHA}" .pre-commit-config.yaml \
    && git add *.txt *.cpp .pre-commit*.yaml \
    && git commit -m 'Initial commit' \
    && pre-commit run --all-files && success=1 || success=0
rm -rf .git

if [ $success -eq 0 ]; then
    exit 1
fi
popd

pushd tests/cmake_bad
git init \
    && git config user.name 'Test' \
    && git config user.email 'test@test.com' \
    && call_sed -i "/rev: /c\\    rev: ${LATEST_SHA}" .pre-commit-config.yaml \
    && git add *.txt *.cpp .pre-commit*.yaml \
    && git commit -m 'Initial commit' \
    && pre-commit run --all-files && success=0 || success=1
rm -rf .git

if [ $success -eq 0 ]; then
    exit 1
fi
popd
