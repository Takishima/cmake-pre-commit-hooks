cmake_minimum_required(VERSION 3.15)
project(cmake_bad LANGUAGES CXX)
add_library(mylib STATIC bad.cpp)
