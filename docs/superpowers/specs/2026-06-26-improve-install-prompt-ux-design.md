---
comet_change: improve-install-prompt-ux
role: technical-design
canonical_spec: openspec
archived-with: 2026-06-26-improve-install-prompt-ux
status: final
---

# Install Prompt UX Improvement — Technical Design

## Overview

Replace the `readline`-based text input in the `diagram-to-image` interactive installer with `@inquirer/prompts` checkbox (agent multi-select) and select (scope choice). Use a top-level feature-flag dispatch pattern so the inquirer path runs when the dependency is available, and the existing readline logic serves as a transparent fallback.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  lib/cli.js                          │
│                                                     │
│  // Top-level: detect inquirer availability         │
│  let inquirerAvailable = false;                     │
│  try { require('@inquirer/prompts');                 │
│         inquirerAvailable = true; } catch {}         │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │  promptForAgents()                           │   │
│  │    if (inquirerAvailable)                    │   │
│  │      → promptForAgentsInquirer() [checkbox]  │   │
│  │    else                                      │   │
│  │      → promptForAgentsLegacy() [readline]    │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │  promptForScope()                            │   │
│  │    if (inquirerAvailable)                    │   │
│  │      → promptForScopeInquirer() [select]     │   │
│  │    else                                      │   │
│  │      → promptForScopeLegacy() [readline]     │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
│  The run() function and all callers are unchanged.  │
│  Function signatures are identical.                 │
└─────────────────────────────────────────────────────┘
```

## Component Details

### 1. Inquirer Availability Flag

```js
let inquirerAvailable = false;
try {
  require('@inquirer/prompts');
  inquirerAvailable = true;
} catch {
  // @inquirer/prompts not installed or corrupted — fall back to readline
}
```

Single top-level check. If the `require` throws (missing dep, corrupted node_modules), the flag stays `false` and all prompt functions delegate to legacy readline.

### 2. promptForAgentsInquirer()

```js
async function promptForAgentsInquirer({ input, output } = {}) {
  const { checkbox } = require('@inquirer/prompts');
  const agents = enabledAgents();
  const selected = await checkbox({
    message: 'Select agents to install:',
    choices: agents.map(a => ({
      name: `${a.displayName} (${a.id})`,
      value: a.id,
      checked: true,
    })),
    required: true,
  });
  return selected;
}
```

- `checked: true` — all agents selected by default (matches current behavior of "all agents" when no selection provided)
- `required: true` — prevents empty submission
- Ignores `input`/`output` params — `@inquirer/prompts` manages its own TTY interaction

### 3. promptForScopeInquirer()

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

- `default: 'global'` — matches current behavior

### 4. Legacy Functions

`promptForAgentsLegacy()` and `promptForScopeLegacy()` are the existing `promptForAgents()` and `promptForScope()` implementations, renamed. They retain the exact `readline`-based text input logic and the `{ input, output }` parameter handling.

### 5. Dispatch Wrappers

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

### 6. Module Exports Update

```js
module.exports = {
  // ... existing exports ...
  promptForAgents,
  promptForScope,
  promptForAgentsLegacy,   // exported for tests
  promptForScopeLegacy,    // exported for tests
};
```

Legacy functions remain exported so existing tests can exercise the readline path directly.

## Data Flow (unchanged)

```
run() [line 213-223]
  │
  ├─ promptForAgents() ──→ agentIds: string[]
  │
  ├─ promptForScope()  ──→ scope: 'global' | 'project'
  │
  └─ installSkillToAgents({ agentIds, scope, packageRoot })
```

No changes to `run()`, `parseCliArgs()`, or any other function. The callers consume the same return types from the same function names.

## Error Handling

| Scenario | Behavior |
|----------|----------|
| `@inquirer/prompts` not installed | Top-level `require` throws → `inquirerAvailable = false` → legacy readline used |
| TTY not available + inquirer available | `@inquirer/prompts` throws internally → caught by inquirer → we wrap in try/catch within inquirer functions, fall through to legacy |
| User passes `--agent` / `--scope` / `--all` | `promptForAgents`/`promptForScope` never called; `resolveInstallAgentIds` uses CLI args directly |
| Non-TTY stdin (pipe, CI) | `input.isTTY` is `false` in `run()` → skips all prompts → installs to all agents globally |

## Testing

- **Existing tests**: `promptForAgentsLegacy` / `promptForScopeLegacy` exported and testable; no behavioral change
- **Manual — TTY interactive**: Run `node bin/diagram-to-image.js`, verify checkbox and select render correctly, selections propagate to install
- **Manual — CLI args**: `diagram-to-image install --agent claude-code --scope project` skips prompts
- **Manual — Non-TTY**: `echo | node bin/diagram-to-image.js` installs all agents globally without prompting
- **Manual — Fallback**: Remove `@inquirer/prompts` from `node_modules`, verify legacy readline prompts appear
