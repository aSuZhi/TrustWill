import "dotenv/config";
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

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

function loadRuntimeConfig(configPath) {
  return JSON.parse(fs.readFileSync(configPath, "utf8"));
}

function resolveOwner(config, chainId) {
  const entry = (config.owners || []).find((item) => Number(item.chain_id) === Number(chainId));
  if (!entry?.owner) {
    throw new Error(`No owner configured for chain ${chainId}`);
  }
  return entry.owner;
}

function inspectTriggeredWill({ configPath, owner, chainId }) {
  const runtimeRoot = process.cwd();
  const skillRoot = path.resolve(runtimeRoot, "..");
  const watcherScript = path.join(skillRoot, "scripts", "will_watcher.py");
  const command = [
    "python",
    watcherScript,
    "inspect-owner",
    "--config",
    configPath,
    "--owner",
    owner,
    "--chain-id",
    String(chainId)
  ];
  const stdout = execFileSync(command[0], command.slice(1), { encoding: "utf8" });
  const inspections = JSON.parse(stdout);
  const inspection = inspections[0];
  if (!inspection) {
    throw new Error(`No will inspection result for chain ${chainId}`);
  }
  if (inspection.status_label !== "Triggered") {
    if (inspection.status_label === "Claimed") {
      throw new Error(`Will on chain ${chainId} has already been claimed`);
    }
    throw new Error(`Will is not triggered yet on chain ${chainId}. Current status: ${inspection.status_label}`);
  }
  if (!Array.isArray(inspection.authorized_tokens) || inspection.authorized_tokens.length === 0) {
    throw new Error(`Triggered will on chain ${chainId} has no authorized tokens`);
  }
  return inspection;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const runtimeRoot = process.cwd();
  const configPath = path.resolve(runtimeRoot, args.config || path.join("config", "will.runtime.json"));
  const config = loadRuntimeConfig(configPath);
  const chainId = Number(args["chain-id"] || 196);
  const owner = args.owner || resolveOwner(config, chainId);

  const inspection = inspectTriggeredWill({ configPath, owner, chainId });
  const chain = (config.chains || []).find((item) => Number(item.chain_id) === chainId);
  if (!chain) {
    throw new Error(`Chain ${chainId} not found in runtime config`);
  }

  const baseUrl = args["base-url"] || process.env.CLAIM_DAPP_BASE_URL || "http://127.0.0.1:8787/claim.html";
  const url = new URL(baseUrl);
  url.searchParams.set("chainId", String(chainId));
  url.searchParams.set("chainName", chain.name);
  url.searchParams.set("rpc", chain.rpc_url);
  url.searchParams.set("will", inspection.will_contract);
  url.searchParams.set("beneficiary", inspection.beneficiary);
  url.searchParams.set("owner", inspection.owner);
  url.searchParams.set("tokens", inspection.authorized_tokens.join(","));

  console.log(
    JSON.stringify(
      {
        ok: true,
        chainId,
        chainName: chain.name,
        willContract: inspection.will_contract,
        beneficiary: inspection.beneficiary,
        owner: inspection.owner,
        tokens: inspection.authorized_tokens,
        claimUrl: url.toString()
      },
      null,
      2
    )
  );
}

main();
