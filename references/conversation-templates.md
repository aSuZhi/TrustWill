# Agentic Wallet Will — Conversation Templates

Use these templates to make the skill feel like a guided product flow instead of a technical script.

## 1. Create Flow

### Intent opener

User says:

- `创建一个信托合约`
- `帮我创建遗嘱合约`
- `create a wallet will`

Assistant:

`可以。我会先帮你确认触发时间、受益地址，再检查当前钱包里可纳入遗嘱的 ERC-20 资产。这个 v1 版本只覆盖 ERC-20，不包含原生 ETH/BNB。触发时间可以用分钟、小时或天。`

### Missing trigger days

Assistant:

`你希望触发时间设为多久？例如 1 分钟、12 小时、20 天。`

### Missing beneficiary

Assistant:

`受益人地址是什么？请直接发一个 0x 开头的 EVM 地址。`

### Fixed trigger explanation

Assistant:

`这个版本的触发条件是固定的：到达你设定的时间时，如果最后一段监控窗口内没有通过 Agentic Wallet 发起主动操作，就会进入可领取状态。长周期默认用更长窗口，短周期测试会自动缩短。`

### Pre-write summary

Assistant:

`我将为你创建链上遗嘱，配置如下：

- 触发时间：{trigger_days} 天
- 触发条件：到期前最后一段监控窗口无 Agentic Wallet 主动操作
- 受益地址：{beneficiary}
- 覆盖链：{chains}
- 将纳入遗嘱的 ERC-20：{token_summary}

提醒：v1 不包含原生 ETH / BNB / OKB 等 gas 币，新买入的代币也不会自动纳入。

如果你确认，我就开始创建合约并授权这些代币。`

### Pre-write summary when no ERC-20 holdings exist yet

Assistant:

`我将先为你创建一个空壳链上遗嘱，配置如下：

- 触发时间：{trigger_days} 天
- 触发条件：到期前最后一段监控窗口无 Agentic Wallet 主动操作
- 受益地址：{beneficiary}
- 覆盖链：{chains}
- 当前纳入遗嘱的 ERC-20：暂无，创建后你可以再追加授权

提醒：v1 不包含原生 ETH / BNB / OKB 等 gas 币。你后续只要往钱包转入 ERC-20，再说“把当前新持仓也加入遗嘱”，我就能帮你补登记和授权。

如果你确认，我现在就先创建空壳遗嘱合约。`

### Create success

Assistant:

`已创建完成。

- 遗嘱合约：{will_addresses}
- 已登记代币：{token_summary}
- 触发时间：{trigger_days} 天
- 监控窗口：自动计算

后续你可以直接说“查看当前绑定的信托合约”来查看详情，或说“把当前新持仓也加入遗嘱”来补授权新代币。`

### Create success for empty-shell will

Assistant:

`已创建完成。

- 遗嘱合约：{will_addresses}
- 当前状态：空壳遗嘱，暂未登记 ERC-20
- 触发时间：{trigger_days} 天
- 监控窗口：自动计算

后续你只要把 ERC-20 转进这个钱包，再说“把当前新持仓也加入遗嘱”，我就可以继续补授权。`

## 2. Inspect Flow

### Query opener

Assistant:

`我正在检查当前钱包在所有支持链上绑定的信托合约。`

### No will found

Assistant:

`当前没有检测到已绑定的信托合约。你可以直接说“创建一个信托合约”，我会一步步带你完成。`

### Compact result

Assistant:

`当前绑定情况如下：

- {chain_name}: {status_label}
  合约：{will_contract}
  受益人：{beneficiary}
  触发时间：{trigger_days} 天
  截止时间：{deadline}
  授权状态：{approval_state_summary}`

### Compact result when claimable

Assistant:

`当前绑定情况如下：

- {chain_name}: Triggered
  合约：{will_contract}
  受益人：{beneficiary}
  截止时间：{deadline}
  授权状态：{approval_state_summary}

这份遗嘱已经进入可领取状态。你现在可以直接说“受益人领取”，我会自动为你生成本地领取链接。`

### Expanded token detail

Assistant:

`{chain_name} 的授权代币明细：

- {token_a}: 余额 {balance_a}，授权 {allowance_state_a}
- {token_b}: 余额 {balance_b}，授权 {allowance_state_b}`

## 3. Modify Flow

### Ambiguous modify request

User says:

- `修改我的信托合约`

Assistant:

`可以。你是想修改受益人地址，还是修改触发时间，或者把当前新持仓加入遗嘱？`

### Update beneficiary summary

Assistant:

`我将把受益人从 {old_beneficiary} 改为 {new_beneficiary}。其他配置不变。确认后我就发起链上更新。`

### Update trigger days summary

Assistant:

`我将把触发时间从 {old_days} 天改为 {new_days} 天。其他配置不变。确认后我就发起链上更新。`

### Add tokens summary

Assistant:

`我发现这些新持仓还没有纳入遗嘱：{new_tokens}。

如果你确认，我会把它们登记到现有遗嘱合约，并完成对应授权。`

### Modify success

Assistant:

`修改已完成。你可以现在说“查看当前绑定的信托合约”，我帮你核对最新配置。`

## 4. Cancel Flow

### Cancel summary

Assistant:

`我将执行两步操作：

- 取消当前遗嘱合约状态
- 撤销该遗嘱合约对已登记 ERC-20 的授权

涉及链：{chains}
涉及合约：{will_addresses}
涉及代币：{token_summary}

确认后我才会开始执行。`

### Cancel success

Assistant:

`已完成取消。

- 已取消的遗嘱合约：{will_addresses}
- 已撤销授权的代币：{revoked_tokens}

如果你之后还想重新设置，可以再次说“创建一个信托合约”。`

### Partial revoke

Assistant:

`遗嘱状态已取消，但以下代币授权撤销失败，需要重试：

- {failed_tokens}`

## 5. Claim Flow

### Claim not ready

Assistant:

`当前这个遗嘱还没有进入可领取状态，所以现在不能 claim。你可以先查看它的当前状态和截止时间。`

### Claim summary

Assistant:

`这份遗嘱已经进入可领取状态。我会先为受益人生成一个专用领取页面链接，受益人钱包打开后连接钱包，点一下领取按钮就可以发起 claim。

- 目标合约：{will_contract}
- 领取资产：{token_summary}
- 受益人：{beneficiary}`

### Claim success

Assistant:

`领取链接已经生成。我已经在后台自动准备好了本地领取页服务，受益人钱包打开这个 DApp 地址后，就能直接进入领取页面并点击按钮领取。`

### Claim success with detail

Assistant:

`这份遗嘱已经进入可领取状态，我已经为受益人准备好了领取页面。

- 链：{chain_name}
- 遗嘱合约：{will_contract}
- 受益人：{beneficiary}
- 可领取资产：{token_summary}

本地领取链接：
{claim_url}

请用受益人钱包打开这个链接，连接钱包后点击“领取已授权资产”即可。`

### Claim already completed

Assistant:

`这份遗嘱已经领取完成。

- 链：{chain_name}
- 状态：Claimed
- 遗嘱合约：{will_contract}

这说明受益人已经成功完成领取，所以现在不会再生成新的领取链接。`

### Claim still active

Assistant:

`当前这份遗嘱还没有进入可领取状态，所以现在不能领取。

- 链：{chain_name}
- 状态：{status_label}
- 截止时间：{deadline}

等它进入 Triggered 后，你再说“受益人领取”，我会直接为你生成领取链接。`

## 6. Validation Messages

### Invalid trigger days

Assistant:

`触发时间至少需要 1 分钟。你可以直接回复例如 1 分钟、12 小时或 20 天。`

### Invalid beneficiary

Assistant:

`这个受益人地址看起来不是标准的 0x EVM 地址。请发一个 0x 开头、42 位长度的地址。`

### XKO address

Assistant:

`XKO 地址格式暂不支持。请先切换到常用地址并找到对应的 0x 地址后再继续。`

### No supported ERC-20 holdings

Assistant:

`我检查了当前钱包，暂时没有发现可纳入遗嘱的 ERC-20 资产。这个版本不包含原生 ETH / BNB / OKB，不过你现在仍然可以先创建一个空壳遗嘱，之后再追加授权资产。`

## 7. Tone Rules

- Start with the next useful step, not with long background explanation
- Use product-like wording such as `我来帮你检查`, `确认后我就执行`, `我先带你完成`
- When the user asks something broad, narrow it with one short follow-up question
- When a write action is about to happen, always make the consequence explicit
