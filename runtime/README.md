# Agentic Wallet Will Runtime / Agentic Wallet 链上遗嘱运行层

This runtime powers the `agentic-wallet-will` skill: deployment, config bootstrap, self-hosted watcher execution, and beneficiary claim-link generation.

这个 runtime 是 `agentic-wallet-will` skill 的运行层，负责合约部署、配置生成、自托管 watcher 触发，以及受益人领取链接生成。

## What It Does / 它能做什么

- Create per-user will / trust contracts on supported EVM chains
- Support natural-language flows in the skill: create, inspect, modify, cancel, add assets, and claim
- Monitor inactivity and mark a will as `Triggered`
- Let each user run their own watcher signer instead of relying on a shared platform watcher
- Generate a beneficiary claim page link for local preview or public hosting

- 在支持的 EVM 链上为每个用户创建独立遗嘱 / 信托合约
- 支持 skill 的自然语言流程：创建、查看、修改、取消、追加资产、受益人领取
- 监控 inactivity 条件并把遗嘱状态切到 `Triggered`
- 让每个用户运行自己的 watcher signer，而不是依赖共享平台 watcher
- 为受益人生成本地或公网领取页面链接

## Current Scope / 当前范围

- EVM only
- ERC-20 only in v1
- Native gas tokens like `ETH / BNB / OKB` are not auto-included
- Newly deployed contracts support minute-, hour-, and day-based trigger durations

- 当前仅支持 EVM
- v1 仅支持 ERC-20
- `ETH / BNB / OKB` 这类原生币不会自动纳入
- 新部署的合约支持按分钟、小时、天设置触发时间

## Web3 Stack / Web3 技术栈

- `Solidity`: will controller and factory contracts
- `EVM`: multi-chain deployment and execution model
- `ERC-20`: `approve`, `allowance`, `balanceOf`, `transferFrom`
- `ethers.js v6`: deployment, contract reads, writes, and wallet-connected claim flow
- `RPC providers`: chain access for BNB Chain, X Layer, Ethereum, Base, Arbitrum, and Polygon
- `Off-chain watcher`: inactivity monitoring and `markTriggered` execution
- `Wallet-connected DApp`: beneficiary claim page for browser wallet interaction
- `ABI / calldata tooling`: helper scripts for encoding and runtime interoperability

- `Solidity`：遗嘱控制器与工厂合约
- `EVM`：多链部署与执行模型
- `ERC-20`：`approve`、`allowance`、`balanceOf`、`transferFrom`
- `ethers.js v6`：部署、读写合约、连接钱包领取
- `RPC providers`：访问 BNB Chain、X Layer、Ethereum、Base、Arbitrum、Polygon
- `Off-chain watcher`：监控 inactivity 条件并执行 `markTriggered`
- `Wallet-connected DApp`：受益人浏览器钱包领取页面
- `ABI / calldata tooling`：编码辅助脚本和运行时互操作工具

## Runtime Layout / 目录说明

- `contracts/`: Solidity contracts used for deployment
- `scripts/`: compile, deploy, bootstrap, claim-link, and trigger helpers
- `watcher/`: polling and activity adapter runtime
- `dapp/`: beneficiary claim page
- `config/`: generated runtime config and deployment records

- `contracts/`：部署用 Solidity 合约
- `scripts/`：编译、部署、bootstrap、领取链接、触发辅助脚本
- `watcher/`：轮询与活跃度适配器
- `dapp/`：受益人领取页面
- `config/`：运行配置和部署记录

## Install / 安装

From this directory:

在当前目录执行：

```powershell
npm install
```

## Environment / 环境变量

Copy `.env.example` to `.env`, then fill in only what you actually need.

把 `.env.example` 复制成 `.env`，再按需填写。

Typical fields:

常见字段：

- `DEPLOYER_PRIVATE_KEY`: the private key of your own watcher signer
- `WATCHER_ADDRESS`: your own watcher address written into newly created wills
- `*_RPC_URL`: per-chain RPC endpoints
- `CLAIM_DAPP_BASE_URL`: optional public claim page base URL

- `DEPLOYER_PRIVATE_KEY`：你自己的 watcher 签名钱包私钥
- `WATCHER_ADDRESS`：写入新遗嘱合约中的你自己的 watcher 地址
- `*_RPC_URL`：各链 RPC 地址
- `CLAIM_DAPP_BASE_URL`：可选的公网领取页地址

Security note:

安全提醒：

- Do not keep real secrets in `.env.example`
- Treat any exposed private key as compromised and rotate it

- 不要把真实私钥放在 `.env.example`
- 任何暴露过的私钥都应视为已泄露并立即更换

Watcher note:

Watcher 说明：

- This runtime now assumes a self-hosted watcher model
- Before creating a will, the user should configure their own `WATCHER_ADDRESS` and matching `DEPLOYER_PRIVATE_KEY`
- The watcher wallet must later have enough gas on every chain where automatic triggering is expected

- 当前 runtime 默认采用自托管 watcher 模式
- 创建遗嘱前，用户需要先配置自己的 `WATCHER_ADDRESS` 和对应的 `DEPLOYER_PRIVATE_KEY`
- 如果希望某条链能自动触发，该 watcher 钱包后续必须在那条链上有足够 gas

## Operator Flow / 平台初始化流程

This is the one-time setup path for the skill operator, not for every end user.

这是平台方的一次性初始化流程，不是每个终端用户都要做。

### 1. Compile / 编译

```powershell
npm run compile
```

### 2. Deploy a Factory / 部署工厂合约

Examples:

示例：

```powershell
npm run deploy:bsc
npm run deploy:xlayer
```

Supported deployment scripts:

当前支持的部署脚本：

- `npm run deploy:ethereum`
- `npm run deploy:bsc`
- `npm run deploy:polygon`
- `npm run deploy:xlayer`
- `npm run deploy:arbitrum`
- `npm run deploy:base`

### 3. Bootstrap Runtime Config / 生成运行配置

```powershell
npm run bootstrap
```

This generates:

会生成：

- `config/will.runtime.json`

The bootstrap script will try to auto-detect the currently logged-in Agentic Wallet owner if possible, but it now also requires a valid watcher address in `runtime/.env`.

如果环境允许，bootstrap 会尝试自动识别当前已登录的 Agentic Wallet 地址作为 owner，但现在也会要求你先在 `runtime/.env` 里配置有效的 watcher 地址。

### 4. Run the Watcher / 启动 watcher

```powershell
npm run watcher:poll
```

The watcher checks whether a will has passed its deadline and whether there was no qualifying Agentic Wallet activity in the monitoring window. If true, it can call `markTriggered`.

watcher 会检查遗嘱是否已到期，以及监控窗口内是否没有符合条件的 Agentic Wallet 主动操作；满足条件后会调用 `markTriggered`。

## End User Flow / 终端用户流程

After factories are deployed and runtime config exists, users can create wills without redeploying contracts, but they do need to think about their own watcher configuration.

在工厂合约部署好、runtime 配置存在之后，用户不需要重复部署合约，但仍需要先完成自己的 watcher 配置。

The intended natural-language flow is:

理想的自然语言使用方式是：

- `创建信托合约`
- `查看当前绑定的信托合约`
- `把当前新持仓也加入遗嘱`
- `取消授权的信托合约`
- `受益人领取`

The skill handles the conversational prompts, confirmation steps, and on-chain actions.

skill 会负责多轮追问、二次确认和链上执行。

## Trigger and Claim / 触发与领取

### Trigger / 触发

The will does not auto-transfer immediately on inactivity.

遗嘱不会在“不活跃”时立刻自动转账。

Instead, the runtime works like this:

实际流程是：

1. The will reaches its configured trigger time
2. The watcher verifies the monitoring window
3. The watcher calls `markTriggered`
4. The will becomes `Triggered`

1. 遗嘱达到设定触发时间
2. watcher 检查监控窗口
3. watcher 调用 `markTriggered`
4. 遗嘱状态切到 `Triggered`

### Claim / 领取

Once the will is `Triggered`, the beneficiary can claim registered ERC-20 assets.

一旦遗嘱进入 `Triggered`，受益人就可以领取已登记的 ERC-20 资产。

## Beneficiary Claim DApp / 受益人领取页面

### Serve Locally / 本地启动领取页

```powershell
npm run claim-dapp:serve
```

This serves the claim page at:

默认会在这里启动：

- `http://127.0.0.1:8787/claim.html`

### Generate a Claim Link / 生成领取链接

```powershell
npm run claim-link -- --chain-id 196
```

This generates a link for a `Triggered` will.

它会为一份 `Triggered` 状态的遗嘱生成领取链接。

### One-Step Local Link Prep / 一步式本地领取链接

```powershell
npm run claim-link:local -- --chain-id 196
```

This will:

它会自动：

- ensure the local claim page server is available
- inspect the will state
- generate a ready-to-open localhost claim link

- 确保本地领取页服务可用
- 检查遗嘱状态
- 生成可直接打开的 localhost 领取链接

### Public Hosting / 公网部署

If you want a beneficiary on another device to open the page directly, host `dapp/claim.html` on a public domain and set `CLAIM_DAPP_BASE_URL`.

如果你希望受益人在其他设备上直接打开领取页，请把 `dapp/claim.html` 部署到公网域名，并配置 `CLAIM_DAPP_BASE_URL`。

Good options:

常见选择：

- Vercel
- Netlify
- Cloudflare Pages
- VPS + Nginx

## Typical Commands / 常用命令

```powershell
npm run compile
npm run test
npm run deploy:xlayer
npm run bootstrap
npm run watcher:poll
npm run claim-dapp:serve
npm run claim-link -- --chain-id 196
npm run claim-link:local -- --chain-id 196
```

## Notes / 备注

- A will may exist even if it currently has no registered ERC-20 assets
- Newly added ERC-20 holdings are not included automatically; they must be added and approved
- If a will is already `Claimed`, claim-link generation will refuse to produce a new link
- Public RPCs are fine for testing but not ideal for long-running production watcher workloads

- 遗嘱可以先以空壳形式存在，即使当前还没有登记 ERC-20
- 新增 ERC-20 持仓不会自动纳入，需要后续追加登记与授权
- 如果遗嘱已经是 `Claimed`，领取链接脚本不会再生成新的领取链接
- 公共 RPC 适合测试，但不适合长期生产 watcher

## Related Files / 相关文件

- Skill guide: [`../SKILL.md`](../SKILL.md)
- Conversation templates: [`../references/conversation-templates.md`](../references/conversation-templates.md)
- Claim page: [`dapp/claim.html`](./dapp/claim.html)
- Runtime package: [`package.json`](./package.json)

## Status / 当前状态

This runtime is suitable for local testing, skill integration, and operator-managed deployments on supported chains.

当前这套 runtime 已适合本地测试、skill 集成，以及在已支持链上的平台化部署。
