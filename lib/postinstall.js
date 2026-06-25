const {
  installSkillToAgents,
  parseAgentsEnv,
  packageRootFromLib,
} = require("./install-skill");

function main() {
  let selectedAgents = parseAgentsEnv(process.env.DIAGRAM_TO_IMAGE_AGENTS);
  if (selectedAgents.length === 0) {
    const { enabledAgents } = require("./agent-registry");
    selectedAgents = enabledAgents().map((agent) => agent.id);
  }

  const scope = (process.env.DIAGRAM_TO_IMAGE_SCOPE || "global").toLowerCase();

  const results = installSkillToAgents({
    agentIds: selectedAgents,
    scope,
    packageRoot: packageRootFromLib(),
  });
  for (const result of results) {
    console.log(`Installed ${result.displayName} skill (${scope}) to ${result.targetRoot}`);
  }
  return 0;
}

if (require.main === module) {
  try {
    process.exitCode = main();
  } catch (error) {
    console.error(`diagram-to-image postinstall failed: ${error.message}`);
    process.exitCode = 1;
  }
}

module.exports = { main };
