---
change: improve-install-prompt-ux
design-doc: docs/superpowers/specs/2026-06-26-improve-install-prompt-ux-design.md
base-ref: a5a275359b0f175b6431eae9401049a88c703bd3
---

# Improve Install Prompt UX — Implementation Plan

**Goal:** Replace `readline`-based text input in the interactive installer with `@inquirer/prompts` checkbox (agent multi-select) and select (scope choice), using a feature-flag dispatch pattern.

**Architecture:** Single top-level try/catch for `@inquirer/prompts` sets `inquirerAvailable` flag. Two new inquirer functions implement new UX. Existing readline functions renamed to Legacy. Wrappers dispatch based on flag. `run()` unchanged.

## File Structure

| File | Role | Action |
|------|------|--------|
| `package.json` | Declare runtime dependency | Add `@inquirer/prompts` to dependencies |
| `lib/cli.js` | All prompt logic | Rename legacy, add inquirer, add wrappers, update exports |

---

## Task 1: Add dependency

- [x] 1.1 Add `@inquirer/prompts: "^8.4.3"` to `package.json` dependencies
- [x] 1.2 Run `npm install`
- [x] 1.3 Verify: `node -e "require('@inquirer/prompts')"` exits 0

---

## Task 2: Refactor lib/cli.js

- [x] 2.1 Add inquirer availability flag at top of module (after line 11, before PYTHON_SCRIPTS)

```js
let inquirerAvailable = false;
try {
  require('@inquirer/prompts');
  inquirerAvailable = true;
} catch {
  // @inquirer/prompts not installed or corrupted — fall back to readline
}
```

- [x] 2.2 Rename `promptForScope` (line 109) → `promptForScopeLegacy`
- [x] 2.3 Rename `promptForAgents` (line 130) → `promptForAgentsLegacy`
- [x] 2.4 Add `promptForAgentsInquirer()` after legacy function (before `printAgents`):

```js
async function promptForAgentsInquirer({ input, output } = {}) {
  const { checkbox } = require('@inquirer/prompts');
  const agents = enabledAgents();
  return checkbox({
    message: 'Select agents to install:',
    choices: agents.map(a => ({
      name: `${a.displayName} (${a.id})`,
      value: a.id,
      checked: true,
    })),
    required: true,
  });
}
```

- [x] 2.5 Add `promptForScopeInquirer()` after it:

```js
async function promptForScopeInquirer({ input, output } = {}) {
  const { select } = require('@inquirer/prompts');
  return select({
    message: 'Install scope:',
    choices: [
      { name: 'global  — ~/.codex/skills/ or ~/.claude/skills/ (all projects)', value: 'global' },
      { name: 'project — ./.codex/skills/ or ./.claude/skills/ (this project only)', value: 'project' },
    ],
    default: 'global',
  });
}
```

- [x] 2.6 Add dispatch wrappers:

```js
async function promptForAgents(opts) {
  if (inquirerAvailable) return promptForAgentsInquirer(opts);
  return promptForAgentsLegacy(opts);
}

async function promptForScope(opts) {
  if (inquirerAvailable) return promptForScopeInquirer(opts);
  return promptForScopeLegacy(opts);
}
```

- [x] 2.7 Update `module.exports` to export wrapper + legacy functions
- [x] 2.8 Verify syntax: `node -c lib/cli.js`

---

## Task 3: Verify

- [x] 3.1 Run `npm test` — existing tests pass
- [x] 3.2 Manual smoke test: TTY checkbox/select interaction
- [x] 3.3 Manual smoke test: `--agent` / `--scope` skip prompts
- [x] 3.4 Manual smoke test: non-TTY silent install to all agents
