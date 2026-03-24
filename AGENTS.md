# Agentic Wallet Will Plugin Notes

This repository can be used as an OpenClaw-compatible plugin source.

## What this plugin expects

- The skill itself lives at the repository root and is described by `SKILL.md`
- The runtime helpers live in `runtime/`
- Node.js and Python are required for the runtime scripts
- `onchainos` must already be available on `PATH` if you want wallet login, balance, history, or contract-call flows to work

## Secrets and local config

Do not commit real secrets.

Use:

- `runtime/.env` for local private keys and operator-only settings
- `runtime/.env.example` as the public template

Typical operator-managed values:

- `DEPLOYER_PRIVATE_KEY`
- `WATCHER_ADDRESS`
- `*_RPC_URL`
- `CLAIM_DAPP_BASE_URL`

## OpenClaw-specific note

The plugin exports `openclawPlugin` from `flake.nix`, but the JavaScript runtime dependencies still need to be installed once inside `runtime/` with `npm install` before the deployment and watcher scripts are used.

## Safe defaults

- End users should reuse predeployed factory contracts when available
- End users should not be asked to deploy contracts during normal will creation
- Platform operators can deploy additional chains locally with their own `.env`
