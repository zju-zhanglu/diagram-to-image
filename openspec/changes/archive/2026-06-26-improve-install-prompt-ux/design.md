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
