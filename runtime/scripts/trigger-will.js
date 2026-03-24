import dotenv from "dotenv";
import { ethers } from "ethers";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(SCRIPT_DIR, "..", ".env") });

const CHAIN_RPC_ENVS = {
  1: "ETHEREUM_RPC_URL",
  56: "BSC_RPC_URL",
  137: "POLYGON_RPC_URL",
  196: "XLAYER_RPC_URL",
  8453: "BASE_RPC_URL",
  42161: "ARBITRUM_RPC_URL"
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

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const chainId = Number(args["chain-id"]);
  const willContract = args["will-contract"];
  const activityRef = args["activity-ref"];

  if (!Number.isInteger(chainId) || !CHAIN_RPC_ENVS[chainId]) {
    throw new Error(`Unsupported or missing --chain-id: ${args["chain-id"]}`);
  }
  if (!ethers.isAddress(willContract)) {
    throw new Error(`Invalid --will-contract: ${willContract}`);
  }
  if (!/^0x[a-fA-F0-9]{64}$/.test(activityRef || "")) {
    throw new Error(`Invalid --activity-ref: ${activityRef}`);
  }
  if (!process.env.DEPLOYER_PRIVATE_KEY) {
    throw new Error("Missing DEPLOYER_PRIVATE_KEY in environment");
  }

  const rpcEnv = CHAIN_RPC_ENVS[chainId];
  const rpcUrl = process.env[rpcEnv];
  if (!rpcUrl) {
    throw new Error(`Missing ${rpcEnv} in environment`);
  }

  const provider = new ethers.JsonRpcProvider(rpcUrl, chainId);
  const signer = new ethers.Wallet(process.env.DEPLOYER_PRIVATE_KEY, provider);
  const expectedWatcher = process.env.WATCHER_ADDRESS;
  if (expectedWatcher && ethers.getAddress(expectedWatcher) !== signer.address) {
    throw new Error(
      `DEPLOYER_PRIVATE_KEY address ${signer.address} does not match WATCHER_ADDRESS ${ethers.getAddress(expectedWatcher)}`
    );
  }

  const contract = new ethers.Contract(
    willContract,
    ["function markTriggered(bytes32 activityProofRef) external"],
    signer
  );
  const tx = await contract.markTriggered(activityRef);
  const receipt = await tx.wait();

  console.log(
    JSON.stringify(
      {
        ok: true,
        chainId,
        watcher: signer.address,
        willContract,
        activityRef,
        txHash: receipt.hash,
        blockNumber: receipt.blockNumber
      },
      null,
      2
    )
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
