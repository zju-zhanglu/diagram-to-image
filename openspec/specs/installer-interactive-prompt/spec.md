# installer-interactive-prompt Specification

## Purpose
TBD - created by archiving change improve-install-prompt-ux. Update Purpose after archive.
## Requirements
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

