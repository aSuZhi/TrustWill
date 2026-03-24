import "dotenv/config";
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

const DEFAULT_CHAINS = {
  ethereum: { name: "Ethereum", chain_id: 1, rpc_env: "ETHEREUM_RPC_URL" },
  bsc: { name: "BNB Chain", chain_id: 56, rpc_env: "BSC_RPC_URL" },
  polygon: { name: "Polygon", chain_id: 137, rpc_env: "POLYGON_RPC_URL" },
  xlayer: { name: "X Layer", chain_id: 196, rpc_env: "XLAYER_RPC_URL" },
  arbitrum: { name: "Arbitrum One", chain_id: 42161, rpc_env: "ARBITRUM_RPC_URL" },
  base: { name: "Base", chain_id: 8453, rpc_env: "BASE_RPC_URL" }
};

function parseArgs(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const current = argv[index];
    if (!current.startsWith("--")) {
      continue;
    }
    const key = current.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith("--")) {
      parsed[key] = true;
    } else {
      parsed[key] = next;
      index += 1;
    }
  }
  return parsed;
}

function collectAddresses(payload) {
  const data = payload?.data || {};
  const addresses = [];
  for (const key of ["evm", "xlayer"]) {
    for (const item of data[key] || []) {
      if (typeof item?.address === "string") {
        addresses.push(item.address);
      }
    }
  }
  return addresses;
}

function resolveLoggedInOwner(chains) {
  const triedChains = [];
  for (const chain of chains) {
    triedChains.push(chain.chain_id);
    try {
      const stdout = execFileSync(
        "onchainos",
        ["wallet", "addresses", "--chain", String(chain.chain_id)],
        { encoding: "utf8" }
      );
      const payload = JSON.parse(stdout);
      const addresses = collectAddresses(payload);
      const owner = addresses.find((address) => /^0x[a-fA-F0-9]{40}$/.test(address));
      if (owner) {
        return owner;
      }
    } catch {
      // Try the next configured chain.
    }
  }
  throw new Error(
    `Missing required --owner argument and could not resolve a logged-in Agentic Wallet address from configured chains: ${triedChains.join(", ")}`
  );
}

function loadDeployment(networkName) {
  const deploymentPath = path.join(process.cwd(), "config", "deployments", `${networkName}.json`);
  if (!fs.existsSync(deploymentPath)) {
    return null;
  }
  return JSON.parse(fs.readFileSync(deploymentPath, "utf8"));
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const outputPath = path.join(process.cwd(), "config", "will.runtime.json");
  const activityAdapterPath = path.join(process.cwd(), "watcher", "activity_adapter.py");
  const triggerScriptPath = path.join(process.cwd(), "scripts", "trigger-will.js");
  const chains = [];
  for (const [networkName, metadata] of Object.entries(DEFAULT_CHAINS)) {
    const deployment = loadDeployment(networkName);
    if (!deployment) {
      continue;
    }
    chains.push({
      name: metadata.name,
      chain_id: metadata.chain_id,
      rpc_url: process.env[metadata.rpc_env] || `set-${metadata.rpc_env}`,
      factory_address: deployment.willFactory,
      watcher_address: deployment.defaultWatcher
    });
  }

  if (chains.length === 0) {
    throw new Error("No deployment metadata found. Deploy WillFactory to at least one network before exporting runtime config.");
  }

  const owner = args.owner || resolveLoggedInOwner(chains);
  const runtimeConfig = {
    chains,
    owners: chains.map((chain) => ({
      chain_id: chain.chain_id,
      owner,
      label: args.label || "Primary wallet"
    })),
    activity_command_template:
      `python "${activityAdapterPath}" --owner {owner} --chain-id {chain_id} --begin-ms {begin_ms} --end-ms {end_ms}`,
    trigger_command_template:
      `node "${triggerScriptPath}" --chain-id {chain_id} --will-contract {will_contract} --activity-ref {activity_ref}`,
    dry_run: false
  };

  fs.writeFileSync(outputPath, JSON.stringify(runtimeConfig, null, 2));
  console.log(`Wrote runtime config to ${outputPath}`);
  console.log(JSON.stringify(runtimeConfig, null, 2));
}

try {
  main();
} catch (error) {
  console.error(error);
  process.exit(1);
}
