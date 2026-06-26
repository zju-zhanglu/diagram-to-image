## Why

The current `npx @zju-zhanglu/diagram-to-image` interactive installer uses raw `readline` text input, requiring users to type numbers or IDs to select agents and scope. This is unintuitive and error-prone. Replacing it with checkbox/select prompts (`@inquirer/prompts`) provides a polished, keyboard-driven experience consistent with modern CLI tools (including Comet itself).

## What Changes

- Replace `promptForAgents()` readline text input with `@inquirer/prompts` checkbox multi-select (arrow keys navigate, space toggles, `a` selects all, `i` inverts)
- Replace `promptForScope()` readline text input with `@inquirer/prompts` select single-choice
- Add graceful fallback: if `@inquirer/prompts` fails to load, fall back to existing readline behavior
- Add `@inquirer/prompts` as a production dependency in `package.json`
- Non-TTY and explicit CLI argument behavior remain unchanged

## Capabilities

### New Capabilities

- `installer-interactive-prompt`: Interactive checkbox and select prompts for the installer wizard, replacing raw text input. Covers agent multi-selection via checkbox and scope single-selection via select, with graceful fallback to existing readline behavior.

### Modified Capabilities

<!-- None — existing capabilities are unchanged. -->

## Impact

- `lib/cli.js` — `promptForAgents()` and `promptForScope()` replaced; new fallback wrapper added
- `package.json` — new dependency: `@inquirer/prompts`
- No changes to `lib/agent-registry.js`, `lib/install-skill.js`, `lib/postinstall.js`, `lib/preuninstall.js`
- No breaking changes to CLI interface or exit codes
