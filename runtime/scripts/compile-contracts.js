import fs from "node:fs";
import path from "node:path";
import solc from "solc";

const workspaceRoot = process.cwd();
const entrypoints = [
  path.join("contracts", "WillFactory.sol"),
  path.join("contracts", "WillController.sol"),
  path.join("contracts", "MockToken.sol")
];

function readFile(relativePath) {
  return fs.readFileSync(path.join(workspaceRoot, relativePath), "utf8");
}

function normalizeImport(importPath) {
  return importPath.replaceAll("\\", "/");
}

function resolveImport(fromFile, importPath) {
  const normalized = normalizeImport(importPath);
  if (normalized.startsWith(".")) {
    return path.posix.normalize(path.posix.join(path.posix.dirname(fromFile), normalized));
  }
  return normalized;
}

function collectSources(entryFiles) {
  const sources = new Map();
  const queue = [...entryFiles.map((item) => normalizeImport(item))];

  while (queue.length > 0) {
    const current = queue.pop();
    if (sources.has(current)) {
      continue;
    }

    const content = readFile(current);
    sources.set(current, { content });

    const importRegex = /^\s*import\s+(?:[^'"]+\s+from\s+)?["']([^"']+)["'];/gm;
    for (const match of content.matchAll(importRegex)) {
      queue.push(resolveImport(current, match[1]));
    }
  }

  return Object.fromEntries(sources);
}

function collectArtifacts(output) {
  const artifacts = {};
  for (const [sourceName, contracts] of Object.entries(output.contracts || {})) {
    for (const [contractName, contractData] of Object.entries(contracts)) {
      if (!contractData.evm?.bytecode?.object) {
        continue;
      }
      artifacts[contractName] = {
        contractName,
        sourceName,
        abi: contractData.abi,
        bytecode: `0x${contractData.evm.bytecode.object}`,
        deployedBytecode: `0x${contractData.evm.deployedBytecode.object || ""}`
      };
    }
  }
  return artifacts;
}

function main() {
  const sources = collectSources(entrypoints);
  const input = {
    language: "Solidity",
    sources,
    settings: {
      optimizer: { enabled: true, runs: 200 },
      outputSelection: {
        "*": {
          "*": ["abi", "evm.bytecode.object", "evm.deployedBytecode.object"]
        }
      }
    }
  };

  const output = JSON.parse(solc.compile(JSON.stringify(input)));
  const errors = (output.errors || []).filter((item) => item.severity === "error");
  if (errors.length > 0) {
    for (const error of errors) {
      console.error(error.formattedMessage || error.message);
    }
    process.exit(1);
  }

  const artifacts = collectArtifacts(output);
  const artifactsDir = path.join(workspaceRoot, "artifacts-local");
  fs.mkdirSync(artifactsDir, { recursive: true });

  for (const [contractName, artifact] of Object.entries(artifacts)) {
    fs.writeFileSync(path.join(artifactsDir, `${contractName}.json`), JSON.stringify(artifact, null, 2));
  }

  console.log(`Compiled ${Object.keys(artifacts).length} contracts into ${artifactsDir}`);
}

main();
