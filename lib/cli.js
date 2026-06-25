const { spawnSync } = require("node:child_process");
const path = require("node:path");
const readline = require("node:readline/promises");

const {
  enabledAgents,
  getAgent,
  resolveAgentIds,
} = require("./agent-registry");
const {
  installSkillToAgents,
  parseAgentsEnv,
  packageRootFromLib,
} = require("./install-skill");

const PYTHON_SCRIPTS = {
  extract: "extract_markdown_diagrams.py",
  lint: "lint_drawio_xml.py",
  "select-vision-model": "select_vision_model.py",
};

function usage() {
  return `Usage:
  diagram-to-image install [--agent <id> ... | --all]
  diagram-to-image list-agents
  diagram-to-image status
  diagram-to-image extract [...args]
  diagram-to-image lint [...args]
  diagram-to-image select-vision-model [...args]

Supported agents:
  ${enabledAgents().map((agent) => agent.id).join(", ")}
`;
}

function parseCliArgs(argv) {
  const [command = "help", ...args] = argv;
  const parsed = {
    command,
    args: [],
    agents: [],
    all: false,
    help: false,
  };

  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === "--help" || arg === "-h") {
      parsed.help = true;
    } else if (arg === "--all") {
      parsed.all = true;
    } else if (arg === "--agent") {
      const agentId = args[index + 1];
      if (!agentId) {
        throw new Error("--agent requires an agent id");
      }
      parsed.agents.push(agentId);
      index += 1;
    } else if (arg.startsWith("--agent=")) {
      parsed.agents.push(arg.slice("--agent=".length));
    } else {
      parsed.args.push(arg);
    }
  }

  return parsed;
}

function resolveInstallAgentIds(parsed, { env = process.env, interactive = process.stdin.isTTY } = {}) {
  if (parsed.all) {
    return enabledAgents().map((agent) => agent.id);
  }
  if (parsed.agents.length > 0) {
    return resolveAgentIds(parsed.agents);
  }
  const envAgents = parseAgentsEnv(env.DIAGRAM_TO_IMAGE_AGENTS);
  if (envAgents.length > 0) {
    return envAgents;
  }
  // Default to all agents when no explicit selection is provided
  return enabledAgents().map((agent) => agent.id);
}

async function promptForAgents({ input = process.stdin, output = process.stdout } = {}) {
  const agents = enabledAgents();
  output.write("Select agent targets for diagram-to-image:\n");
  agents.forEach((agent, index) => {
    output.write(`  ${index + 1}. ${agent.displayName} (${agent.id})\n`);
  });
  output.write("  all. All supported agents\n");

  const rl = readline.createInterface({ input, output });
  try {
    const answer = await rl.question("Install to (numbers, ids, or all): ");
    const normalized = answer.trim();
    if (!normalized) {
      throw new Error("No agents selected");
    }
    if (normalized.toLowerCase() === "all") {
      return agents.map((agent) => agent.id);
    }

    const tokens = normalized
      .split(",")
      .map((token) => token.trim())
      .filter(Boolean)
      .map((token) => {
        if (/^\d+$/.test(token)) {
          const agent = agents[Number(token) - 1];
          if (!agent) {
            throw new Error(`Unknown agent selection "${token}"`);
          }
          return agent.id;
        }
        return token;
      });
    return resolveAgentIds(tokens);
  } finally {
    rl.close();
  }
}

function printAgents({ output = process.stdout, context = {} } = {}) {
  for (const agent of enabledAgents()) {
    const detected = agent.detect(context);
    output.write(`${detected.id}\t${detected.displayName}\t${detected.installPath}\n`);
  }
}

function printStatus({ output = process.stdout, context = {} } = {}) {
  for (const agent of enabledAgents()) {
    const detected = agent.detect(context);
    const status = detected.installed ? "installed" : "not installed";
    const rootStatus = detected.skillRootExists ? "skill root exists" : "skill root missing";
    output.write(`${detected.id}\t${status}\t${rootStatus}\t${detected.installPath}\n`);
  }
}

function runPythonScript(command, args, { packageRoot = packageRootFromLib(), stdio = "inherit" } = {}) {
  const scriptName = PYTHON_SCRIPTS[command];
  if (!scriptName) {
    throw new Error(`Unknown Python helper "${command}"`);
  }
  const scriptPath = path.join(packageRoot, "scripts", scriptName);
  const result = spawnSync("python3", [scriptPath, ...args], { stdio });
  if (result.error) {
    throw result.error;
  }
  return result.status || 0;
}

async function run(argv, {
  env = process.env,
  input = process.stdin,
  output = process.stdout,
  error = process.stderr,
  packageRoot = packageRootFromLib(),
} = {}) {
  const parsed = parseCliArgs(argv);

  // Default: auto-install to all agents when no command is given (npx use case)
  if (argv.length === 0) {
    parsed.command = "install";
    parsed.all = true;
  }

  if (parsed.command === "help" || parsed.command === "--help" || parsed.command === "-h") {
    output.write(usage());
    return 0;
  }

  if (parsed.command === "list-agents") {
    printAgents({ output });
    return 0;
  }

  if (parsed.command === "status") {
    printStatus({ output });
    return 0;
  }

  if (parsed.command === "install") {
    const agentIds = resolveInstallAgentIds(parsed, { env, interactive: input.isTTY });
    const results = installSkillToAgents({ agentIds, packageRoot });
    for (const result of results) {
      output.write(`Installed ${result.displayName} skill to ${result.targetRoot}\n`);
    }
    return 0;
  }

  if (Object.prototype.hasOwnProperty.call(PYTHON_SCRIPTS, parsed.command)) {
    const helperArgs = parsed.help ? ["--help", ...parsed.args] : parsed.args;
    return runPythonScript(parsed.command, helperArgs, { packageRoot });
  }

  if (parsed.help) {
    output.write(usage());
    return 0;
  }

  try {
    getAgent(parsed.command);
  } catch (_agentError) {
    error.write(`Unknown command "${parsed.command}".\n\n${usage()}`);
    return 1;
  }

  return 1;
}

module.exports = {
  parseCliArgs,
  printAgents,
  printStatus,
  promptForAgents,
  resolveInstallAgentIds,
  run,
  runPythonScript,
  usage,
};
