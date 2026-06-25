const assert = require("node:assert/strict");
const test = require("node:test");

const {
  parseCliArgs,
  resolveInstallAgentIds,
} = require("../lib/cli");

test("parseCliArgs captures repeated --agent options", () => {
  const parsed = parseCliArgs(["install", "--agent", "codex", "--agent", "claude-code"]);

  assert.equal(parsed.command, "install");
  assert.deepEqual(parsed.agents, ["codex", "claude-code"]);
  assert.equal(parsed.all, false);
});

test("parseCliArgs supports install --all", () => {
  const parsed = parseCliArgs(["install", "--all"]);

  assert.equal(parsed.command, "install");
  assert.equal(parsed.all, true);
});

test("resolveInstallAgentIds uses --agent before environment", () => {
  const parsed = parseCliArgs(["install", "--agent", "codex"]);
  const agentIds = resolveInstallAgentIds(parsed, {
    env: { DIAGRAM_TO_IMAGE_AGENTS: "claude-code" },
    interactive: false,
  });

  assert.deepEqual(agentIds, ["codex"]);
});

test("resolveInstallAgentIds supports environment-selected install targets", () => {
  const parsed = parseCliArgs(["install"]);
  const agentIds = resolveInstallAgentIds(parsed, {
    env: { DIAGRAM_TO_IMAGE_AGENTS: "codex,claude-code" },
    interactive: false,
  });

  assert.deepEqual(agentIds, ["codex", "claude-code"]);
});

test("non-interactive install without selected agents defaults to all", () => {
  const parsed = parseCliArgs(["install"]);
  const agentIds = resolveInstallAgentIds(parsed, { env: {}, interactive: false });

  assert.deepEqual(agentIds, ["codex", "claude-code"]);
});
