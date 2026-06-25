const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const SKILL_DIR_NAME = "diagram-to-image";

function contextValue(context, key, fallback) {
  if (Object.prototype.hasOwnProperty.call(context, key)) {
    return context[key];
  }
  return fallback;
}

function resolveHome(context = {}) {
  const homedir = contextValue(context, "homedir", os.homedir);
  return typeof homedir === "function" ? homedir() : homedir;
}

function rootExists(rootPath) {
  try {
    return fs.statSync(rootPath).isDirectory();
  } catch (_error) {
    return false;
  }
}

function createAgent({ id, displayName, envHomeName, fallbackHomeDir }) {
  function resolveSkillRoot(context = {}) {
    const env = context.env || process.env;
    const configuredHome = env[envHomeName];
    if (configuredHome) {
      return path.join(configuredHome, "skills");
    }
    return path.join(resolveHome(context), fallbackHomeDir, "skills");
  }

  function resolveInstallPath(context = {}) {
    return path.join(resolveSkillRoot(context), SKILL_DIR_NAME);
  }

  function detect(context = {}) {
    const skillRoot = resolveSkillRoot(context);
    const installPath = resolveInstallPath(context);
    return {
      id,
      displayName,
      skillRoot,
      installPath,
      skillRootExists: rootExists(skillRoot),
      installed: rootExists(installPath),
    };
  }

  return {
    id,
    displayName,
    enabled: true,
    detect,
    resolveInstallPath,
  };
}

const SUPPORTED_AGENTS = [
  createAgent({
    id: "codex",
    displayName: "Codex",
    envHomeName: "CODEX_HOME",
    fallbackHomeDir: ".codex",
  }),
  createAgent({
    id: "claude-code",
    displayName: "Claude Code",
    envHomeName: "CLAUDE_HOME",
    fallbackHomeDir: ".claude",
  }),
];

function enabledAgents() {
  return SUPPORTED_AGENTS.filter((agent) => agent.enabled);
}

function supportedAgentIds() {
  return enabledAgents().map((agent) => agent.id);
}

function getAgent(agentId) {
  const agent = SUPPORTED_AGENTS.find((candidate) => candidate.id === agentId);
  if (!agent || !agent.enabled) {
    throw new Error(`Unsupported agent "${agentId}". Supported agents: ${supportedAgentIds().join(", ")}`);
  }
  return agent;
}

function resolveAgentIds(agentIds) {
  const selected = [];
  for (const agentId of agentIds) {
    const normalized = String(agentId || "").trim();
    if (!normalized) {
      continue;
    }
    getAgent(normalized);
    if (!selected.includes(normalized)) {
      selected.push(normalized);
    }
  }
  return selected;
}

module.exports = {
  SKILL_DIR_NAME,
  SUPPORTED_AGENTS,
  enabledAgents,
  getAgent,
  resolveAgentIds,
  supportedAgentIds,
};
