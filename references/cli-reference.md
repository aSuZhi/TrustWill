# Agentic Wallet Will — CLI Reference

This skill uses three kinds of commands:

1. `onchainos wallet ...` for login state, balances, and contract-call execution
2. `python scripts/will_calldata.py ...` for deterministic calldata generation and return decoding
3. `python scripts/will_watcher.py ...` for cross-chain inspection and watcher evaluation

## Config File

Use `--config <path>` or set `AGENTIC_WILL_CONFIG`.

For normal end-user use, prefer bootstrapping the config from the currently logged-in Agentic Wallet account:

```bash
cd .agents/skills/agentic-wallet-will/runtime
npm run bootstrap
```

This writes `config/will.runtime.json` by:

- reading bundled deployment metadata
- auto-detecting the logged-in EVM wallet address
- filling that address into every configured supported chain
- filling your own configured watcher address into every configured supported chain

Before running bootstrap, make sure `runtime/.env` contains:

- `WATCHER_ADDRESS=<your watcher address>`
- `DEPLOYER_PRIVATE_KEY=<the private key for that watcher address>`

Required JSON shape:

```json
{
  "chains": [
    {
      "name": "Ethereum",
      "chain_id": 1,
      "rpc_url": "https://rpc.example.invalid",
      "factory_address": "0x0000000000000000000000000000000000000001",
      "watcher_address": "0x1111111111111111111111111111111111111111"
    }
  ],
  "owners": [
    {
      "chain_id": 1,
      "owner": "0x1111111111111111111111111111111111111111",
      "label": "Primary wallet"
    }
  ],
  "activity_command_template": "python activity_adapter.py --owner {owner} --chain-id {chain_id} --begin-ms {begin_ms} --end-ms {end_ms}",
  "trigger_command_template": "onchainos wallet contract-call --to {will_contract} --chain {chain_id} --input-data {mark_triggered_calldata}",
  "dry_run": true
}
```

`activity_command_template` must print JSON like:

```json
{
  "active": false,
  "activity_ref": "history-window-empty",
  "records": []
}
```

## Chain IDs

| Chain | Chain ID |
|---|---|
| Ethereum | `1` |
| BNB Chain | `56` |
| Polygon | `137` |
| X Layer | `196` |
| Arbitrum One | `42161` |
| Base | `8453` |

## Inspect A Bound Will

Resolve the current EVM address first, or bootstrap the runtime config, then inspect across all configured chains:

```bash
python .agents/skills/agentic-wallet-will/scripts/will_watcher.py \
  inspect-owner \
  --config .agents/skills/agentic-wallet-will/assets/examples/watcher-config.example.json \
  --owner 0xcac3eb8bbdd36ab87bf595f72b5c0c45b75d1335
```

The output includes:

- `will_contract`
- `status`
- `beneficiary`
- `trigger_after_days`
- `deadline`
- `authorized_tokens`
- `allowances[]`

Approval states:

- `max`: allowance is effectively unlimited
- `partial`: allowance exists but is not max
- `missing`: allowance is zero

## Create A Will

### 0. Watcher preflight

Before creating a will, first configure your own watcher locally:

```bash
WATCHER_ADDRESS=0x3333333333333333333333333333333333333333
DEPLOYER_PRIVATE_KEY=0x...
```

The watcher address written into the contract must match the signer private key you will later use for `markTriggered`.

### 1. Encode `createWill`

```bash
python .agents/skills/agentic-wallet-will/scripts/will_calldata.py \
  encode create-will \
  --beneficiary 0x2222222222222222222222222222222222222222 \
  --days 20 \
  --watcher 0x3333333333333333333333333333333333333333
```

### 2. Send the factory call with Agentic Wallet

```bash
onchainos wallet contract-call \
  --to 0xFactoryAddress \
  --chain 56 \
  --input-data 0x...
```

### 3. Read back the new will address

```bash
python .agents/skills/agentic-wallet-will/scripts/will_watcher.py \
  inspect-owner \
  --config config.json \
  --owner 0xYourWallet
```

### 4. Register covered tokens on the will contract

```bash
python .agents/skills/agentic-wallet-will/scripts/will_calldata.py \
  encode register-tokens \
  --tokens 0xTokenA,0xTokenB
```

Then send the calldata with `onchainos wallet contract-call`.

If the wallet currently has no supported ERC-20 holdings, this step can be skipped. The will contract can still be created first as an empty shell, and tokens can be appended later with `addAuthorizedTokens`.

### 5. Approve each token to the will contract

```bash
python .agents/skills/agentic-wallet-will/scripts/will_calldata.py \
  encode approve \
  --spender 0xWillContract \
  --amount max
```

Use the returned calldata as the `--input-data` and send the transaction to the token contract itself:

```bash
onchainos wallet contract-call \
  --to 0xTokenA \
  --chain 56 \
  --input-data 0x...
```

## Modify Beneficiary

```bash
python .agents/skills/agentic-wallet-will/scripts/will_calldata.py \
  encode update-beneficiary \
  --beneficiary 0x4444444444444444444444444444444444444444
```

## Modify Trigger Days

```bash
python .agents/skills/agentic-wallet-will/scripts/will_calldata.py \
  encode update-trigger-days \
  --days 30
```

## Append Newly Held Tokens

1. Inspect the current will
2. Compare current wallet holdings with `authorized_tokens`
3. Encode `addAuthorizedTokens`
4. Send the controller call
5. Send `approve(max)` for each newly appended token

```bash
python .agents/skills/agentic-wallet-will/scripts/will_calldata.py \
  encode add-tokens \
  --tokens 0xTokenC,0xTokenD
```

## Cancel A Will And Revoke Approvals

### 1. Cancel the controller state

```bash
python .agents/skills/agentic-wallet-will/scripts/will_calldata.py encode cancel-will
```

### 2. Revoke token approvals

For each registered token:

```bash
python .agents/skills/agentic-wallet-will/scripts/will_calldata.py \
  encode approve \
  --spender 0xWillContract \
  --amount 0
```

Send each revoke call to the token contract with `onchainos wallet contract-call`.

## Beneficiary Claim

```bash
python .agents/skills/agentic-wallet-will/scripts/will_calldata.py \
  encode claim \
  --tokens 0xTokenA,0xTokenB
```

Send the calldata to the will contract:

```bash
onchainos wallet contract-call \
  --to 0xWillContract \
  --chain 56 \
  --input-data 0x...
```

## Watcher Poll

Run a dry poll:

```bash
python .agents/skills/agentic-wallet-will/scripts/will_watcher.py \
  poll \
  --config .agents/skills/agentic-wallet-will/assets/examples/watcher-config.example.json
```

Execute the configured trigger command for every due will:

```bash
python .agents/skills/agentic-wallet-will/scripts/will_watcher.py \
  poll \
  --config config.json \
  --execute
```
