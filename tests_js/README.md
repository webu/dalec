# Javacript tests

## Install dependencies

You have to install Node.js to run the tests.
We highly recommend the use of [n](https://github.com/tj/n) to install the current LTS version of Node.js.
Once Node.js is set up you can install dependencies with

```bash
npm i
```

## Run tests

We use Jest as our test framework.
To run tests, simply use

```bash
npm test
```

## Code format

To avoid inconsistent formatting between developers, we require the use of [Prettier](https://prettier.io/).
Before commiting, you can run the formatter with

```bash
npm run fmt
```
