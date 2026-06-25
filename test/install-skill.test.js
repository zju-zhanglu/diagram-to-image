const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  SKILL_RESOURCE_PATHS,
  copySkillResources,
  parseAgentsEnv,
} = require("../lib/install-skill");

test("resource list includes only skill-owned resources", () => {
  assert.deepEqual(SKILL_RESOURCE_PATHS, [
    "SKILL.md",
    "README.md",
    "README.zh.md",
    "LICENSE",
    "agents",
    "references",
    "scripts",
  ]);
});

test("parseAgentsEnv supports comma-separated agents and all", () => {
  assert.deepEqual(parseAgentsEnv("codex, claude-code"), ["codex", "claude-code"]);
  assert.deepEqual(parseAgentsEnv("all"), ["codex", "claude-code"]);
  assert.deepEqual(parseAgentsEnv(""), []);
});

test("copySkillResources copies skill resources without npm-only files", () => {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "diagram-to-image-test-"));
  const packageRoot = path.join(tempRoot, "package");
  const targetRoot = path.join(tempRoot, "target");

  fs.mkdirSync(path.join(packageRoot, "agents"), { recursive: true });
  fs.mkdirSync(path.join(packageRoot, "references"), { recursive: true });
  fs.mkdirSync(path.join(packageRoot, "scripts"), { recursive: true });
  fs.mkdirSync(path.join(packageRoot, "bin"), { recursive: true });
  fs.mkdirSync(path.join(packageRoot, "lib"), { recursive: true });
  fs.writeFileSync(path.join(packageRoot, "SKILL.md"), "skill");
  fs.writeFileSync(path.join(packageRoot, "README.md"), "readme");
  fs.writeFileSync(path.join(packageRoot, "README.zh.md"), "readme zh");
  fs.writeFileSync(path.join(packageRoot, "LICENSE"), "license");
  fs.writeFileSync(path.join(packageRoot, "package.json"), "{}");
  fs.writeFileSync(path.join(packageRoot, "agents", "openai.yaml"), "agent");
  fs.writeFileSync(path.join(packageRoot, "references", "guide.md"), "guide");
  fs.writeFileSync(path.join(packageRoot, "scripts", "tool.py"), "print('ok')");
  fs.writeFileSync(path.join(packageRoot, "bin", "diagram-to-image.js"), "bin");
  fs.writeFileSync(path.join(packageRoot, "lib", "agent-registry.js"), "lib");

  const copied = copySkillResources({ packageRoot, targetRoot });

  assert.deepEqual(
    copied.map((entry) => entry.relativePath).sort(),
    SKILL_RESOURCE_PATHS.slice().sort(),
  );
  assert.equal(fs.readFileSync(path.join(targetRoot, "SKILL.md"), "utf8"), "skill");
  assert.equal(fs.existsSync(path.join(targetRoot, "agents", "openai.yaml")), true);
  assert.equal(fs.existsSync(path.join(targetRoot, "bin", "diagram-to-image.js")), false);
  assert.equal(fs.existsSync(path.join(targetRoot, "lib", "agent-registry.js")), false);
  assert.equal(fs.existsSync(path.join(targetRoot, "package.json")), false);
});
