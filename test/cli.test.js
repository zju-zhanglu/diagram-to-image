const assert = require("node:assert/strict");
const test = require("node:test");

const {
  parseCliArgs,
  resolveInstallAgentIds,
  resolveInstallScope,
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

test("parseCliArgs captures --scope flag", () => {
  const parsed = parseCliArgs(["install", "--scope", "project"]);

  assert.equal(parsed.command, "install");
  assert.equal(parsed.scope, "project");
});

test("parseCliArgs supports --scope=project syntax", () => {
  const parsed = parseCliArgs(["install", "--scope=project"]);

  assert.equal(parsed.scope, "project");
});

test("parseCliArgs defaults scope to null", () => {
  const parsed = parseCliArgs(["install"]);

  assert.equal(parsed.scope, null);
});

test("resolveInstallScope prefers --scope flag", () => {
  const parsed = parseCliArgs(["install", "--scope", "project"]);
  const scope = resolveInstallScope(parsed, { env: { DIAGRAM_TO_IMAGE_SCOPE: "global" } });

  assert.equal(scope, "project");
});

test("resolveInstallScope falls back to DIAGRAM_TO_IMAGE_SCOPE env", () => {
  const parsed = parseCliArgs(["install"]);
  const scope = resolveInstallScope(parsed, { env: { DIAGRAM_TO_IMAGE_SCOPE: "project" } });

  assert.equal(scope, "project");
});

test("resolveInstallScope defaults to global", () => {
  const parsed = parseCliArgs(["install"]);
  const scope = resolveInstallScope(parsed, { env: {} });

  assert.equal(scope, "global");
});

test("resolveInstallScope rejects invalid scope", () => {
  const parsed = parseCliArgs(["install", "--scope", "invalid"]);

  assert.throws(
    () => resolveInstallScope(parsed, { env: {} }),
    /Invalid scope "invalid"/,
  );
});
