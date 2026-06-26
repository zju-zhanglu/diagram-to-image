## 1. Dependencies

- [x] 1.1 Add `@inquirer/prompts` to `package.json` dependencies

## 2. Core Implementation

- [x] 2.1 Implement `promptForAgents()` with `@inquirer/prompts` checkbox, wrapped in try/catch fallback to existing readline behavior
- [x] 2.2 Implement `promptForScope()` with `@inquirer/prompts` select, wrapped in try/catch fallback to existing readline behavior
- [x] 2.3 Update `run()` to use new prompt functions (signatures unchanged, no wiring changes needed)

## 3. Verification

- [x] 3.1 Manual smoke test: run `node bin/diagram-to-image.js` in TTY, verify checkbox and select prompts display correctly
- [x] 3.2 Manual smoke test: run with `--agent` and `--scope` flags, verify prompts are skipped
- [x] 3.3 Manual smoke test: pipe input to simulate non-TTY, verify silent install to all agents
- [x] 3.4 Existing tests pass: `npm test`
