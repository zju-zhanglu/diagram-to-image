const fs = require("node:fs");
const path = require("node:path");

const {
  enabledAgents,
  getAgent,
  resolveAgentIds,
} = require("./agent-registry");

const SKILL_RESOURCE_PATHS = [
  "SKILL.md",
  "README.md",
  "README.zh.md",
  "LICENSE",
  "agents",
  "references",
  "scripts",
];

function packageRootFromLib() {
  return path.resolve(__dirname, "..");
}

function ensureParentDirectory(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function removeIfTypeMismatch(sourcePath, targetPath) {
  if (!fs.existsSync(targetPath)) {
    return;
  }
  const sourceStat = fs.statSync(sourcePath);
  const targetStat = fs.statSync(targetPath);
  if (sourceStat.isDirectory() !== targetStat.isDirectory()) {
    fs.rmSync(targetPath, { recursive: true, force: true });
  }
}

function copyRecursive(sourcePath, targetPath) {
  const sourceStat = fs.statSync(sourcePath);
  removeIfTypeMismatch(sourcePath, targetPath);
  if (sourceStat.isDirectory()) {
    fs.mkdirSync(targetPath, { recursive: true });
    for (const entry of fs.readdirSync(sourcePath, { withFileTypes: true })) {
      copyRecursive(path.join(sourcePath, entry.name), path.join(targetPath, entry.name));
    }
    return;
  }
  ensureParentDirectory(targetPath);
  fs.copyFileSync(sourcePath, targetPath);
}

function copySkillResources({ packageRoot = packageRootFromLib(), targetRoot }) {
  if (!targetRoot) {
    throw new Error("targetRoot is required");
  }

  const copied = [];
  fs.mkdirSync(targetRoot, { recursive: true });
  for (const relativePath of SKILL_RESOURCE_PATHS) {
    const sourcePath = path.join(packageRoot, relativePath);
    if (!fs.existsSync(sourcePath)) {
      continue;
    }
    const targetPath = path.join(targetRoot, relativePath);
    copyRecursive(sourcePath, targetPath);
    copied.push({ relativePath, sourcePath, targetPath });
  }
  return copied;
}

function parseAgentsEnv(value) {
  const normalized = String(value || "").trim();
  if (!normalized) {
    return [];
  }
  if (normalized.toLowerCase() === "all") {
    return enabledAgents().map((agent) => agent.id);
  }
  return resolveAgentIds(normalized.split(",").map((part) => part.trim()));
}

function installSkillToAgents({
  agentIds,
  scope = "global",
  packageRoot = packageRootFromLib(),
  context = {},
} = {}) {
  const selectedAgentIds = resolveAgentIds(agentIds || []);
  if (selectedAgentIds.length === 0) {
    throw new Error("No agents selected");
  }

  const installContext = { ...context, scope };
  return selectedAgentIds.map((agentId) => {
    const agent = getAgent(agentId);
    const targetRoot = agent.resolveInstallPath(installContext);
    const copied = copySkillResources({ packageRoot, targetRoot });
    return {
      agentId,
      displayName: agent.displayName,
      scope,
      targetRoot,
      copied,
    };
  });
}

function uninstallSkillFromAgents({
  agentIds,
  scopes = ["global", "project"],
  context = {},
} = {}) {
  const selectedAgentIds = resolveAgentIds(agentIds || []);
  if (selectedAgentIds.length === 0) {
    throw new Error("No agents selected");
  }

  const results = [];
  for (const scope of scopes) {
    const uninstallContext = { ...context, scope };
    for (const agentId of selectedAgentIds) {
      const agent = getAgent(agentId);
      const targetRoot = agent.resolveInstallPath(uninstallContext);
      const existed = fs.existsSync(targetRoot);
      if (existed) {
        fs.rmSync(targetRoot, { recursive: true, force: true });
      }
      results.push({
        agentId,
        displayName: agent.displayName,
        scope,
        targetRoot,
        removed: existed,
      });
    }
  }
  return results;
}

module.exports = {
  SKILL_RESOURCE_PATHS,
  copySkillResources,
  installSkillToAgents,
  parseAgentsEnv,
  packageRootFromLib,
  uninstallSkillFromAgents,
};
