const assert = require("node:assert/strict");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  SUPPORTED_AGENTS,
  getAgent,
  resolveAgentIds,
} = require("../lib/agent-registry");

test("registry exposes codex and claude-code as enabled agents", () => {
  assert.deepEqual(
    SUPPORTED_AGENTS.filter((agent) => agent.enabled).map((agent) => agent.id),
    ["codex", "claude-code"],
  );
});

test("codex install path prefers CODEX_HOME", () => {
  const agent = getAgent("codex");
  const installPath = agent.resolveInstallPath({
    env: { CODEX_HOME: "/tmp/custom-codex" },
    homedir: () => "/home/example",
  });

  assert.equal(installPath, path.join("/tmp/custom-codex", "skills", "diagram-to-image"));
});

test("claude-code install path falls back to ~/.claude", () => {
  const agent = getAgent("claude-code");
  const installPath = agent.resolveInstallPath({
    env: {},
    homedir: () => "/home/example",
  });

  assert.equal(installPath, path.join("/home/example", ".claude", "skills", "diagram-to-image"));
});

test("detect reports whether an agent skill root exists", () => {
  const agent = getAgent("codex");
  const tempDir = os.tmpdir();
  const detected = agent.detect({
    env: { CODEX_HOME: tempDir },
    homedir: () => "/home/example",
  });

  assert.equal(detected.id, "codex");
  assert.equal(detected.installPath, path.join(tempDir, "skills", "diagram-to-image"));
  assert.equal(typeof detected.skillRootExists, "boolean");
});

test("unknown agent ids fail with a clear message", () => {
  assert.throws(
    () => resolveAgentIds(["codex", "future-agent"]),
    /Unsupported agent "future-agent".*codex, claude-code/,
  );
});
