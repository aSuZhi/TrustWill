import "dotenv/config";
import fs from "node:fs";
import path from "node:path";
import { ethers } from "ethers";
import { execFileSync } from "node:child_process";

const NETWORKS = {
  ethereum: { chainId: 1, rpcEnv: "ETHEREUM_RPC_URL", label: "Ethereum" },
  bsc: { chainId: 56, rpcEnv: "BSC_RPC_URL", label: "BNB Chain" },
  polygon: { chainId: 137, rpcEnv: "POLYGON_RPC_URL", label: "Polygon" },
  xlayer: { chainId: 196, rpcEnv: "XLAYER_RPC_URL", label: "X Layer" },
  arbitrum: { chainId: 42161, rpcEnv: "ARBITRUM_RPC_URL", label: "Arbitrum One" },
  base: { chainId: 8453, rpcEnv: "BASE_RPC_URL", label: "Base" }
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

function ensureAddress(value, fieldName) {
  if (!ethers.isAddress(value)) {
    throw new Error(`Invalid ${fieldName}: ${value}`);
  }
  return ethers.getAddress(value);
}

function loadArtifact(contractName) {
  const artifactPath = path.join(process.cwd(), "artifacts-local", `${contractName}.json`);
  if (!fs.existsSync(artifactPath)) {
    execFileSync(process.execPath, [path.join(process.cwd(), "scripts", "compile-contracts.js")], { stdio: "inherit" });
  }
  return JSON.parse(fs.readFileSync(artifactPath, "utf8"));
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const networkName = args.network;
  if (!networkName || !NETWORKS[networkName]) {
    throw new Error(`Missing or unsupported --network. Supported values: ${Object.keys(NETWORKS).join(", ")}`);
  }

  const network = NETWORKS[networkName];
  const rpcUrl = process.env[network.rpcEnv];
  if (!rpcUrl) {
    throw new Error(`Missing ${network.rpcEnv} in environment`);
  }
  if (!process.env.DEPLOYER_PRIVATE_KEY) {
    throw new Error("Missing DEPLOYER_PRIVATE_KEY in environment");
  }

  const provider = new ethers.JsonRpcProvider(rpcUrl, network.chainId);
  const deployer = new ethers.Wallet(process.env.DEPLOYER_PRIVATE_KEY, provider);
  const watcherAddress = ensureAddress(args.watcher || process.env.WATCHER_ADDRESS || deployer.address, "watcher address");
  const artifact = loadArtifact("WillFactory");

  console.log(`Deploying WillFactory to ${network.label} (${network.chainId})`);
  console.log(`Deployer: ${deployer.address}`);
  console.log(`Default watcher: ${watcherAddress}`);

  const contractFactory = new ethers.ContractFactory(artifact.abi, artifact.bytecode, deployer);
  const contract = await contractFactory.deploy(watcherAddress);
  const receipt = await contract.deploymentTransaction().wait();

  const payload = {
    network: networkName,
    label: network.label,
    chainId: network.chainId,
    deployedAt: new Date().toISOString(),
    deployer: deployer.address,
    defaultWatcher: watcherAddress,
    willFactory: await contract.getAddress(),
    deploymentTxHash: receipt.hash,
    blockNumber: receipt.blockNumber
  };

  const outputDir = path.join(process.cwd(), "config", "deployments");
  fs.mkdirSync(outputDir, { recursive: true });
  const outputPath = path.join(outputDir, `${networkName}.json`);
  fs.writeFileSync(outputPath, JSON.stringify(payload, null, 2));

  console.log(JSON.stringify(payload, null, 2));
  console.log(`Saved deployment metadata to ${outputPath}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
