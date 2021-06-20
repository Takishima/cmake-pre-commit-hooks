$build_dir = "build"

Set-PSDebug -trace 1

Function run_hook
{
    Param($Hook, $Src, $ExpectSuccess, $GenCompileDB)

    mkdir -Path $build_dir -Force
    rm -Recurse -Force $build_dir/*

    if ($GenCompileDB -eq 1) {
        Write-Output "$hook -S $Src -B $build_dir -G Ninja $Args"
        & $hook -S $Src -B $build_dir -G Ninja @Args
    }
    else {
        Write-Output "$hook $Args"
        & $hook @Args
    }
    $ret=$LastExitCode

    if ($ExpectSuccess -eq 1) {
        if ($ret -ne 0) {
            echo "Hook $hook failed on source directory $Src with exit code $ret!"
            Exit 1
        }
    }
    else {
        if ($ret -eq 0) {
            echo "Hook $hook unexpectedly succeeded on source directory $Src with exit code $ret!"
            Exit 1
        }
    }

    if ($GenCompileDB -eq 1) {
        if (Test-Path -Path $build_dir/compile_commands.json -PathType leaf) {
            echo "Hook $hook failed to generate the compile database for $Src!"
            Exit 1
        }
    }
}

run_hook -Hook cmake-pc-clang-format-hook -Src tests/cmake_good -ExpectSuccess 1 -GenCompileDB 0 tests/cmake_good/good.cpp
run_hook -Hook cmake-pc-clang-tidy-hook -Src tests/cmake_good -ExpectSuccess 1 -GenCompileDB 1 --checks=readability-magic-numbers --warnings-as-errors=* tests/cmake_good/good.cpp
run_hook -Hook cmake-pc-cppcheck-hook -Src tests/cmake_good -ExpectSuccess 1 -GenCompileDB 1 tests/cmake_good/good.cpp
run_hook -Hook cmake-pc-clang-format-hook -Src tests/cmake_bad -ExpectSuccess 0 -GenCompileDB 0 tests/cmake_bad/bad.cpp
run_hook -Hook cmake-pc-clang-tidy-hook -Src tests/cmake_bad -ExpectSuccess 0 -GenCompileDB 1 --checks=readability-magic-numbers --warnings-as-errors=* tests/cmake_bad/bad.cpp
run_hook -Hook cmake-pc-cppcheck-hook -Src tests/cmake_bad -ExpectSuccess 0 -GenCompileDB 1 tests/cmake_bad/bad.cpp
