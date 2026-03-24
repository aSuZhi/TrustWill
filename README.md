# Agentic Wallet Will Skill

Natural-language will / trust skill for OKX Agentic Wallet.

面向 OKX Agentic Wallet 的自然语言链上遗嘱 / 信托 skill。

## What It Does / 它能做什么

- Create a will contract from natural language
- Inspect the currently bound will
- Modify beneficiary or trigger time
- Add new ERC-20 holdings into the will
- Cancel a will and revoke token approvals
- Generate a beneficiary claim link after the will is triggered

- 用自然语言创建遗嘱合约
- 查看当前绑定的信托 / 遗嘱
- 修改受益人或触发时间
- 把新的 ERC-20 持仓加入遗嘱
- 取消遗嘱并撤销授权
- 在遗嘱触发后为受益人生成领取链接

## Repository Layout / 仓库结构

- `SKILL.md`: skill behavior and conversational workflow
- `references/`: templates and operator-facing reference docs
- `runtime/`: contracts, scripts, watcher, and claim DApp
- `assets/`: reusable contract assets
- `scripts/`: helper tooling shared by the skill

## Install / 安装

Install this repository as a skill source, then enable the skill in your Codex-compatible environment.

把这个仓库作为 skill 源安装到你的 Codex 兼容环境，然后启用这个 skill。

## Main Docs / 主要文档

- Skill guide: [`SKILL.md`](./SKILL.md)
- Runtime guide: [`runtime/README.md`](./runtime/README.md)

## Notes / 备注

- v1 focuses on EVM + ERC-20 flows
- Native gas tokens are not auto-included
- Public RPCs are okay for testing, but dedicated RPCs are better for production

- v1 主要支持 EVM + ERC-20
- 原生 gas 币不会自动纳入
- 公共 RPC 适合测试，生产环境建议使用专用 RPC
