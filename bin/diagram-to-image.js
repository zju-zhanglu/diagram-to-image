#!/usr/bin/env node

const { run } = require("../lib/cli");

run(process.argv.slice(2)).then(
  (status) => {
    process.exitCode = status;
  },
  (error) => {
    console.error(error.message);
    process.exitCode = 1;
  },
);
