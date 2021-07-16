$build_dir = "build"
$CMakeArgs = '-GNinja', '-DCMAKE_C_COMPILER="cl.exe"', '-DCMAKE_CXX_COMPILER="cl.exe"'

Set-PSDebug -trace 1

Function run_hook
{
    Param($Hook,
          $Src,
          $ExpectSuccess,
          $GenCompileDB)


    mkdir -Path $build_dir -Force
    rm -Recurse -Force $build_dir/*

    if ($GenCompileDB -eq 1) {
        Write-Output "$hook -S $Src -B $build_dir $CMakeArgs $Args"
        & $hook -S $Src -B $build_dir @CMakeArgs @Args
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
        if (-not (Test-Path -Path $build_dir/compile_commands.json -PathType Leaf)) {
            echo "Hook $hook failed to generate the compile database for $Src!"
            Exit 1
        }
    }
}

# ==============================================================================

run_hook -Hook cmake-pc-clang-format-hook -Src tests/cmake_good -ExpectSuccess 1 -GenCompileDB 0 tests/cmake_good/good.cpp
run_hook -Hook cmake-pc-clang-tidy-hook -Src tests/cmake_good -ExpectSuccess 1 -GenCompileDB 1 --checks=readability-magic-numbers --warnings-as-errors=* tests/cmake_good/good.cpp
run_hook -Hook cmake-pc-cppcheck-hook -Src tests/cmake_good -ExpectSuccess 1 -GenCompileDB 1 tests/cmake_good/good.cpp

mkdir -Path $build_dir -Force
rm -Recurse -Force $build_dir/*
cmake -B other_build -S tests/cmake_good @CMakeArgs
cmake-pc-cppcheck-hook -S tests/cmake_good -B build -B other_build @CMakeArgs tests/cmake_good/good.cpp
if (-not (Test-Path -Path other_build/compile_commands.json -PathType Leaf)) {
    echo "Failed to generate the compile database for other_build!"
    Exit 1
}

# ------------------------------------------------------------------------------

run_hook -Hook cmake-pc-clang-format-hook -Src tests/cmake_bad -ExpectSuccess 0 -GenCompileDB 0 tests/cmake_bad/bad.cpp
run_hook -Hook cmake-pc-clang-tidy-hook -Src tests/cmake_bad -ExpectSuccess 0 -GenCompileDB 1 --checks=readability-magic-numbers --warnings-as-errors=* tests/cmake_bad/bad.cpp
run_hook -Hook cmake-pc-cppcheck-hook -Src tests/cmake_bad -ExpectSuccess 0 -GenCompileDB 1 tests/cmake_bad/bad.cpp

# ==============================================================================

if (-not (Test-Path env:GITHUB_SHA)) {
    $LATEST_SHA = git rev-parse HEAD
}
else {
    $LATEST_SHA = $env:GITHUB_SHA
}

cd tests/cmake_good
git init
git config user.name 'Test'
git config user.email 'test@test.com'
cp .pre-commit-win.yaml .pre-commit-win.yaml.bak
((Get-Content -path .pre-commit-win.yaml -Raw) -replace 'rev:.*',"rev: $LATEST_SHA") | Set-Content -Path .pre-commit-win.yaml
git add *.txt *.cpp .pre-commit*.yaml
git commit -m 'Initial commit'
pre-commit run -c .pre-commit-win.yaml --all-files
$ret=$?
mv -Force .pre-commit-win.yaml.bak .pre-commit-win.yaml
rm -Force -Recurse .git
if ($ret -eq 0) {
    echo "Pre-commit on tests/cmake_good failed!"
    Exit 1
}
cd ../..

cd tests/cmake_bad
git init
git config user.name 'Test'
git config user.email 'test@test.com'
cp .pre-commit-win.yaml .pre-commit-win.yaml.bak
((Get-Content -path .pre-commit-win.yaml -Raw) -replace 'rev:.*',"rev: $LATEST_SHA") | Set-Content -Path .pre-commit-win.yaml
git add *.txt *.cpp .pre-commit*.yaml
git commit -m 'Initial commit'
pre-commit run -c .pre-commit-win.yaml --all-files
$ret=$?
mv -Force .pre-commit-win.yaml.bak .pre-commit-win.yaml
rm -Force -Recurse .git
if ($ret -eq 1) {
    echo "Pre-commit on tests/cmake_bad unexpectedly passed!"
    Exit 1
}
cd ../..

Exit 0
