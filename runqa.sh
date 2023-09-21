#!/bin/sh

cd tests_js
nodeenv --prebuilt -p
npm i
npm run fmt-check
cd ../
black --check ./
flake8
mypy -p dalec -p dalec_prime -p dalec_example
coverage report -m
coverage erase
