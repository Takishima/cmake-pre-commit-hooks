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

run_hook cmake-pc-clang-format-hook tests/cmake_good 1 0 tests/cmake_good/good.cpp
run_hook cmake-pc-clang-tidy-hook tests/cmake_good 1 1 --checks=readability-magic-numbers --warnings-as-errors=* tests/cmake_good/good.cpp
run_hook cmake-pc-cppcheck-hook tests/cmake_good 1 1 tests/cmake_good/good.cpp

run_hook cmake-pc-clang-format-hook tests/cmake_bad 0 0 tests/cmake_bad/bad.cpp
run_hook cmake-pc-clang-tidy-hook tests/cmake_bad 0 1 --checks=readability-magic-numbers --warnings-as-errors=* tests/cmake_bad/bad.cpp
run_hook cmake-pc-cppcheck-hook tests/cmake_bad 0 1 tests/cmake_bad/bad.cpp
