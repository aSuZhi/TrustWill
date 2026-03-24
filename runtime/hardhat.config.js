import "dotenv/config";
import "@nomicfoundation/hardhat-ethers";

function sharedNetwork(urlEnv, chainId) {
  const url = process.env[urlEnv];
  const accounts = process.env.DEPLOYER_PRIVATE_KEY ? [process.env.DEPLOYER_PRIVATE_KEY] : [];
  if (!url) {
    return undefined;
  }
  return {
    url,
    chainId,
    accounts
  };
}

const configuredNetworks = Object.fromEntries(
  Object.entries({
    ethereum: sharedNetwork("ETHEREUM_RPC_URL", 1),
    bsc: sharedNetwork("BSC_RPC_URL", 56),
    polygon: sharedNetwork("POLYGON_RPC_URL", 137),
    xlayer: sharedNetwork("XLAYER_RPC_URL", 196),
    arbitrum: sharedNetwork("ARBITRUM_RPC_URL", 42161),
    base: sharedNetwork("BASE_RPC_URL", 8453)
  }).filter(([, value]) => value)
);

const config = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts"
  },
  networks: configuredNetworks
};

export default config;
