const {
  enabledAgents,
} = require("./agent-registry");
const {
  parseAgentsEnv,
  uninstallSkillFromAgents,
} = require("./install-skill");

function main() {
  let selectedAgents = parseAgentsEnv(process.env.DIAGRAM_TO_IMAGE_AGENTS);
  if (selectedAgents.length === 0) {
    selectedAgents = enabledAgents().map((agent) => agent.id);
  }

  const scopeEnv = (process.env.DIAGRAM_TO_IMAGE_SCOPE || "").toLowerCase();
  const scopes = scopeEnv === "global" || scopeEnv === "project"
    ? [scopeEnv]
    : ["global", "project"];

  const results = uninstallSkillFromAgents({
    agentIds: selectedAgents,
    scopes,
  });

  let removedCount = 0;
  for (const result of results) {
    if (result.removed) {
      console.log(`Removed ${result.displayName} skill (${result.scope}) from ${result.targetRoot}`);
      removedCount += 1;
    }
  }

  if (removedCount === 0) {
    console.log("No diagram-to-image skill installations found to remove.");
  }
  return 0;
}

if (require.main === module) {
  try {
    process.exitCode = main();
  } catch (error) {
    console.error(`diagram-to-image preuninstall failed: ${error.message}`);
    process.exitCode = 1;
  }
}

module.exports = { main };
