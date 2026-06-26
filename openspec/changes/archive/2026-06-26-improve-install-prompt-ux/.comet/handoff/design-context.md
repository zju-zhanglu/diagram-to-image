# Comet Design Handoff

- Change: improve-install-prompt-ux
- Phase: design
- Mode: compact
- Context hash: 5746f834199ac9610a26c9a47d41bc4395fee644b15d48637cfd5c558ec3e685

Generated-by: comet-handoff.sh

OpenSpec remains the canonical capability spec. This handoff is a deterministic, source-traceable context pack, not an agent-authored summary.

## openspec/changes/improve-install-prompt-ux/proposal.md

- Source: openspec/changes/improve-install-prompt-ux/proposal.md
- Lines: 1-28
- SHA256: be50ab2911ff893b2caece77bc80da59f9de0068c8113db97124b2622cf8dc46

```md
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
```

## openspec/changes/improve-install-prompt-ux/design.md

- Source: openspec/changes/improve-install-prompt-ux/design.md
- Lines: 1-47
- SHA256: 015fa7b4d0e2c2c92ce94ef5c2bff18a4de1a95f007d63ca22e8a92ecb2d783f

```md
## Context

The `diagram-to-image` CLI (`lib/cli.js`) provides an interactive installation wizard when invoked via `npx` without arguments. Currently, `promptForAgents()` and `promptForScope()` use Node.js `readline` for text-based input (typing numbers or IDs). This is functional but not user-friendly.

The Comet skill (`@rpamis/comet`) uses `@inquirer/prompts` for its `comet init` command, providing checkbox (multi-select) and select (single-choice) prompts with arrow-key navigation. This is the reference implementation.

## Goals / Non-Goals

**Goals:**
- Replace readline text input with `@inquirer/prompts` checkbox for agent multi-selection
- Replace readline text input with `@inquirer/prompts` select for scope single-selection
- Maintain graceful fallback when `@inquirer/prompts` cannot be loaded
- Preserve existing non-TTY and explicit-argument behavior unchanged

**Non-Goals:**
- No changes to install logic, agent registry, or other CLI commands
- No new CLI flags
- No changes to `postinstall.js` or `preuninstall.js`

## Decisions

### Decision 1: Use `@inquirer/prompts` (same library as Comet)

**Rationale**: `@inquirer/prompts` is the modern successor to `inquirer`, maintained by the same team. Comet already uses it successfully. It provides exactly the checkbox and select primitives needed. At ~100KB it's a lightweight addition.

**Alternatives considered**:
- `inquirer` (legacy) — older API, larger footprint, less maintained
- `prompts` — similar API but smaller community
- Raw ANSI escape codes — zero dependency but ~150 lines of custom state-machine code, fragile across terminals

### Decision 2: Wrap in a try/catch fallback, not a dynamic import check

**Rationale**: The `@inquirer/prompts` import is synchronous at the top of the module. If it throws (e.g., corrupted install), we catch and set a flag. The prompt functions check this flag and delegate to existing readline functions. This is simpler than dynamic `import()` and maintains synchronous function signatures.

### Decision 3: Two separate prompt functions replaced independently

Each prompt function (`promptForAgents`, `promptForScope`) is replaced with a new implementation that uses the inquirer primitive, wrapped in a fallback that delegates to the original readline version. The function signatures remain unchanged.

### Decision 4: Keep `cli.js` as CommonJS

The project is CommonJS (`require`/`module.exports`). `@inquirer/prompts` supports both ESM and CJS. No module system change needed.

## Risks / Trade-offs

- **New dependency risk** → Mitigation: `@inquirer/prompts` is widely used (10M+ weekly downloads), maintained by the `inquirer` team. If it becomes unavailable, the try/catch fallback ensures the installer still works via readline.
- **TTY detection edge cases** → Mitigation: `@inquirer/prompts` handles non-TTY internally (throws with a clear message). We catch this and fall through to readline, which also handles non-TTY gracefully.
- **Bundle size increase** → The package is already distributed via npm; the dependency is fetched on install. No runtime impact on the skill itself (only the installer CLI).
```

## openspec/changes/improve-install-prompt-ux/tasks.md

- Source: openspec/changes/improve-install-prompt-ux/tasks.md
- Lines: 1-16
- SHA256: c9142eb42c863de2b5e384512d3d4a99725c05c10f6ddc46d2e739240b17503e

```md
## 1. Dependencies

- [ ] 1.1 Add `@inquirer/prompts` to `package.json` dependencies

## 2. Core Implementation

- [ ] 2.1 Implement `promptForAgents()` with `@inquirer/prompts` checkbox, wrapped in try/catch fallback to existing readline behavior
- [ ] 2.2 Implement `promptForScope()` with `@inquirer/prompts` select, wrapped in try/catch fallback to existing readline behavior
- [ ] 2.3 Update `run()` to use new prompt functions (signatures unchanged, no wiring changes needed)

## 3. Verification

- [ ] 3.1 Manual smoke test: run `node bin/diagram-to-image.js` in TTY, verify checkbox and select prompts display correctly
- [ ] 3.2 Manual smoke test: run with `--agent` and `--scope` flags, verify prompts are skipped
- [ ] 3.3 Manual smoke test: pipe input to simulate non-TTY, verify silent install to all agents
- [ ] 3.4 Existing tests pass: `npm test`
```

## openspec/changes/improve-install-prompt-ux/specs/installer-interactive-prompt/spec.md

- Source: openspec/changes/improve-install-prompt-ux/specs/installer-interactive-prompt/spec.md
- Lines: 1-41
- SHA256: 9a3c25d384e4558789ab25846cc9aab5fc2a35abaf2c894cc60b3fe45599128f

```md
## ADDED Requirements

### Requirement: Checkbox multi-select for agent selection

When the installer runs interactively (TTY available), the system SHALL present agent selection as a checkbox prompt where users navigate with arrow keys, toggle with space, select all with `a`, invert selection with `i`, and submit with enter.

#### Scenario: Interactive agent selection with checkbox
- **WHEN** user runs `npx @zju-zhanglu/diagram-to-image` or `diagram-to-image install` in a TTY without `--agent` or `--all` flags
- **THEN** system displays a checkbox prompt listing all supported agents (e.g., "Claude Code", "Codex") with space-toggle and arrow-key navigation
- **AND** at least one agent MUST be selected before submission

#### Scenario: All agents pre-selected by default
- **WHEN** the checkbox prompt is displayed
- **THEN** all supported agents are checked by default

### Requirement: Select prompt for scope choice

When the installer runs interactively, the system SHALL present scope selection as a select (radio) prompt where users navigate with arrow keys and confirm with enter.

#### Scenario: Interactive scope selection with select
- **WHEN** user has completed agent selection in interactive mode
- **THEN** system displays a select prompt with "global" (default, highlighted) and "project" options
- **AND** "global" is the default selection

### Requirement: Graceful fallback on dependency load failure

If `@inquirer/prompts` fails to load, the system SHALL fall back to the existing readline-based text input for both agent and scope prompts without crashing.

#### Scenario: Fallback to readline on import error
- **WHEN** `@inquirer/prompts` cannot be required (e.g., corrupted install)
- **THEN** agent selection falls back to numbered text input via readline
- **AND** scope selection falls back to numbered text input via readline
- **AND** installation proceeds normally

### Requirement: Non-TTY behavior unchanged

When stdin is not a TTY, the system SHALL skip all interactive prompts and install to all agents with global scope, matching existing behavior.

#### Scenario: Pipe or CI environment skips prompts
- **WHEN** stdin is not a TTY (e.g., `echo | npx ...` or CI environment)
- **THEN** system installs to all agents with global scope without displaying any prompts
```

