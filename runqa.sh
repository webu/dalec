#!/bin/sh

cd tests_js
nodeenv --prebuilt -p lts
npm i
npm run fmt-check
cd ../
black --check ./
flake8
mypy -p dalec -p dalec_prime -p dalec_example
coverage report -m
coverage erase

export DJANGO_SETTINGS_MODULE="tests.settings"
if ! django-admin makemigrations --check; then
    >&2 echo "Des migrations sont manquantes et doivent être générées"
    django-admin makemigrations --dry-run
    exit 1
fi