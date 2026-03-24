#!/usr/bin/env python3
"""Cross-chain inspection and watcher polling for Agentic Wallet will contracts."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from will_calldata import build_method_payload, decode_address, decode_address_array, decode_uint256, decode_will_config, normalize_address

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
MAX_APPROVAL_THRESHOLD = (1 << 255)


@dataclass(frozen=True)
class ChainConfig:
    name: str
    chain_id: int
    rpc_url: str
    factory_address: str
    watcher_address: str


@dataclass(frozen=True)
class OwnerRegistration:
    chain_id: int
    owner: str
    label: str | None = None


@dataclass(frozen=True)
class TokenAllowanceState:
    token: str
    balance: int
    allowance: int
    approval_state: str


@dataclass(frozen=True)
class WillInspection:
    chain_id: int
    chain_name: str
    factory_address: str
    owner: str
    will_contract: str
    status: int
    status_label: str
    beneficiary: str | None
    trigger_after_seconds: int | None
    monitor_window_seconds: int | None
    deadline: int | None
    deadline_iso: str | None
    created_at: int | None
    last_trigger_update_at: int | None
    watcher: str | None
    claimable: bool
    activity_proof_ref: str | None
    authorized_tokens: list[str]
    allowances: list[TokenAllowanceState]
    approval_complete: bool | None


@dataclass(frozen=True)
class ActivityWindow:
    active: bool
    activity_ref: str
    records: list[dict[str, Any]]


@dataclass(frozen=True)
class TriggerDecision:
    should_trigger: bool
    reason: str
    activity_ref: str


def iso_timestamp(unix_seconds: int | None) -> str | None:
    if unix_seconds is None:
        return None
    return dt.datetime.fromtimestamp(unix_seconds, tz=dt.timezone.utc).isoformat()


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_chain_configs(data: dict[str, Any]) -> list[ChainConfig]:
    return [
        ChainConfig(
            name=item["name"],
            chain_id=int(item["chain_id"]),
            rpc_url=item["rpc_url"],
            factory_address=normalize_address(item["factory_address"]),
            watcher_address=normalize_address(item["watcher_address"]),
        )
        for item in data.get("chains", [])
    ]


def parse_owner_registrations(data: dict[str, Any]) -> list[OwnerRegistration]:
    return [
        OwnerRegistration(
            chain_id=int(item["chain_id"]),
            owner=normalize_address(item["owner"]),
            label=item.get("label"),
        )
        for item in data.get("owners", [])
    ]


def json_rpc(rpc_url: str, method: str, params: list[Any]) -> Any:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8")
    request = urllib.request.Request(
        rpc_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        result = json.loads(response.read().decode("utf-8"))
    if "error" in result:
        raise RuntimeError(f"json-rpc error: {result['error']}")
    return result["result"]


def eth_call(rpc_url: str, to: str, data: str) -> str:
    return json_rpc(rpc_url, "eth_call", [{"to": to, "data": data}, "latest"])


def resolve_chain(chains: list[ChainConfig], chain_id: int) -> ChainConfig:
    for chain in chains:
        if chain.chain_id == chain_id:
            return chain
    raise KeyError(f"chain_id {chain_id} is not configured")


def approval_state_from_allowance(allowance: int) -> str:
    if allowance == 0:
        return "missing"
    if allowance >= MAX_APPROVAL_THRESHOLD:
        return "max"
    return "partial"


def inspect_will(chain: ChainConfig, owner: str) -> WillInspection:
    owner_to_will_call = build_method_payload("owner-to-will", argparse.Namespace(owner=owner))
    will_contract = decode_address(eth_call(chain.rpc_url, chain.factory_address, owner_to_will_call))
    if will_contract == ZERO_ADDRESS:
        return WillInspection(
            chain_id=chain.chain_id,
            chain_name=chain.name,
            factory_address=chain.factory_address,
            owner=owner,
            will_contract=ZERO_ADDRESS,
            status=-1,
            status_label="None",
            beneficiary=None,
            trigger_after_seconds=None,
            monitor_window_seconds=None,
            deadline=None,
            deadline_iso=None,
            created_at=None,
            last_trigger_update_at=None,
            watcher=None,
            claimable=False,
            activity_proof_ref=None,
            authorized_tokens=[],
            allowances=[],
            approval_complete=None,
        )

    config_call = build_method_payload("get-will-config", argparse.Namespace())
    config = decode_will_config(eth_call(chain.rpc_url, will_contract, config_call))

    tokens_call = build_method_payload("get-authorized-tokens", argparse.Namespace())
    authorized_tokens = decode_address_array(eth_call(chain.rpc_url, will_contract, tokens_call))

    allowances: list[TokenAllowanceState] = []
    approval_complete = True
    for token in authorized_tokens:
        balance_call = build_method_payload("balance-of", argparse.Namespace(owner=owner))
        allowance_call = build_method_payload("allowance", argparse.Namespace(owner=owner, spender=will_contract))
        balance = decode_uint256(eth_call(chain.rpc_url, token, balance_call))
        allowance = decode_uint256(eth_call(chain.rpc_url, token, allowance_call))
        state = approval_state_from_allowance(allowance)
        if state != "max":
            approval_complete = False
        allowances.append(TokenAllowanceState(token=token, balance=balance, allowance=allowance, approval_state=state))

    return WillInspection(
        chain_id=chain.chain_id,
        chain_name=chain.name,
        factory_address=chain.factory_address,
        owner=owner,
        will_contract=will_contract,
        status=config.status,
        status_label=config.status_label,
        beneficiary=config.beneficiary,
        trigger_after_seconds=config.trigger_after_seconds,
        monitor_window_seconds=config.monitor_window_seconds,
        deadline=config.deadline,
        deadline_iso=iso_timestamp(config.deadline),
        created_at=config.created_at,
        last_trigger_update_at=config.last_trigger_update_at,
        watcher=config.watcher,
        claimable=config.status == 1,
        activity_proof_ref=config.activity_proof_ref,
        authorized_tokens=authorized_tokens,
        allowances=allowances,
        approval_complete=approval_complete,
    )


def inspect_owner(chains: list[ChainConfig], owner: str, chain_id: int | None = None) -> list[WillInspection]:
    selected = [resolve_chain(chains, chain_id)] if chain_id is not None else chains
    return [inspect_will(chain, normalize_address(owner)) for chain in selected]


def run_activity_template(template: str, *, owner: str, chain: ChainConfig, begin_ms: int, end_ms: int) -> ActivityWindow:
    rendered = template.format(owner=owner, chain_id=chain.chain_id, chain_name=chain.name, begin_ms=begin_ms, end_ms=end_ms)
    completed = subprocess.run(rendered, shell=True, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "activity command failed"
        raise RuntimeError(message)
    payload = json.loads(completed.stdout)
    return ActivityWindow(
        active=bool(payload.get("active", False)),
        activity_ref=str(payload.get("activity_ref") or "activity-template"),
        records=list(payload.get("records") or []),
    )


def derive_activity_ref(owner: str, chain_id: int, begin_ms: int, end_ms: int) -> str:
    digest = hashlib.sha256(f"{owner}:{chain_id}:{begin_ms}:{end_ms}".encode("utf-8")).hexdigest()
    return "0x" + digest[:64]


def evaluate_trigger(inspection: WillInspection, now_ts: int, activity: ActivityWindow) -> TriggerDecision:
    if inspection.will_contract == ZERO_ADDRESS:
        return TriggerDecision(False, "no will bound", activity.activity_ref)
    if inspection.status_label != "Active":
        return TriggerDecision(False, f"will status is {inspection.status_label}", activity.activity_ref)
    if inspection.deadline is None or now_ts < inspection.deadline:
        return TriggerDecision(False, "deadline not reached", activity.activity_ref)
    if activity.active:
        return TriggerDecision(False, "activity detected in the final monitoring window", activity.activity_ref)
    return TriggerDecision(True, "deadline reached and no Agentic Wallet activity was observed", activity.activity_ref)


def render_trigger_command(template: str, inspection: WillInspection, activity_ref: str) -> str:
    payload = build_method_payload("mark-triggered", argparse.Namespace(activity_ref=activity_ref))
    return template.format(
        chain_id=inspection.chain_id,
        chain_name=inspection.chain_name,
        will_contract=inspection.will_contract,
        owner=inspection.owner,
        activity_ref=activity_ref,
        mark_triggered_calldata=payload,
    )


def inspection_to_dict(inspection: WillInspection) -> dict[str, Any]:
    return {
        "chain_id": inspection.chain_id,
        "chain_name": inspection.chain_name,
        "factory_address": inspection.factory_address,
        "owner": inspection.owner,
        "will_contract": inspection.will_contract,
        "status": inspection.status,
        "status_label": inspection.status_label,
        "beneficiary": inspection.beneficiary,
        "trigger_after_seconds": inspection.trigger_after_seconds,
        "monitor_window_seconds": inspection.monitor_window_seconds,
        "deadline": inspection.deadline,
        "deadline_iso": inspection.deadline_iso,
        "created_at": inspection.created_at,
        "created_at_iso": iso_timestamp(inspection.created_at),
        "last_trigger_update_at": inspection.last_trigger_update_at,
        "last_trigger_update_at_iso": iso_timestamp(inspection.last_trigger_update_at),
        "watcher": inspection.watcher,
        "claimable": inspection.claimable,
        "activity_proof_ref": inspection.activity_proof_ref,
        "authorized_tokens": inspection.authorized_tokens,
        "allowances": [asdict(item) for item in inspection.allowances],
        "approval_complete": inspection.approval_complete,
    }


def command_inspect_owner(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    chains = parse_chain_configs(config)
    inspections = inspect_owner(chains, args.owner, args.chain_id)
    print(json.dumps([inspection_to_dict(item) for item in inspections], ensure_ascii=False, indent=2))
    return 0


def command_poll(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    chains = parse_chain_configs(config)
    owners = parse_owner_registrations(config)
    activity_template = config.get("activity_command_template")
    trigger_template = config.get("trigger_command_template")
    dry_run = bool(config.get("dry_run", True))
    now_ts = int(time.time())
    decisions: list[dict[str, Any]] = []

    for registration in owners:
        chain = resolve_chain(chains, registration.chain_id)
        try:
            inspection = inspect_will(chain, registration.owner)
        except Exception as error:  # noqa: BLE001
            decisions.append(
                {
                    "owner": registration.owner,
                    "label": registration.label,
                    "chain_id": chain.chain_id,
                    "chain_name": chain.name,
                    "should_trigger": False,
                    "reason": f"inspection failed: {error}",
                }
            )
            continue
        if inspection.deadline is None or inspection.monitor_window_seconds is None:
            decisions.append(
                {
                    "owner": registration.owner,
                    "label": registration.label,
                    "chain_id": chain.chain_id,
                    "chain_name": chain.name,
                    "will_contract": inspection.will_contract,
                    "should_trigger": False,
                    "reason": "no active will found",
                }
            )
            continue

        begin_ms = max(0, (inspection.deadline - inspection.monitor_window_seconds) * 1000)
        end_ms = inspection.deadline * 1000
        if activity_template:
            try:
                activity = run_activity_template(activity_template, owner=registration.owner, chain=chain, begin_ms=begin_ms, end_ms=end_ms)
                activity_ref = activity.activity_ref if activity.activity_ref.startswith("0x") else derive_activity_ref(
                    registration.owner, chain.chain_id, begin_ms, end_ms
                )
            except Exception as error:  # noqa: BLE001
                decisions.append(
                    {
                        "owner": registration.owner,
                        "label": registration.label,
                        "chain_id": chain.chain_id,
                        "chain_name": chain.name,
                        "will_contract": inspection.will_contract,
                        "status": inspection.status_label,
                        "deadline": inspection.deadline,
                        "deadline_iso": inspection.deadline_iso,
                        "should_trigger": False,
                        "reason": f"activity check failed: {error}",
                    }
                )
                continue
        else:
            activity_ref = derive_activity_ref(registration.owner, chain.chain_id, begin_ms, end_ms)
            activity = ActivityWindow(active=False, activity_ref=activity_ref, records=[])

        decision = evaluate_trigger(inspection, now_ts, activity)
        entry: dict[str, Any] = {
            "owner": registration.owner,
            "label": registration.label,
            "chain_id": chain.chain_id,
            "chain_name": chain.name,
            "will_contract": inspection.will_contract,
            "status": inspection.status_label,
            "deadline": inspection.deadline,
            "deadline_iso": inspection.deadline_iso,
            "should_trigger": decision.should_trigger,
            "reason": decision.reason,
            "activity_ref": activity_ref,
        }

        if decision.should_trigger and trigger_template:
            entry["command"] = render_trigger_command(trigger_template, inspection, activity_ref)
            if args.execute and not dry_run:
                completed = subprocess.run(entry["command"], shell=True, capture_output=True, text=True, check=False)
                entry["command_exit_code"] = completed.returncode
                entry["command_stdout"] = completed.stdout.strip()
                entry["command_stderr"] = completed.stderr.strip()

        decisions.append(entry)

    print(json.dumps(decisions, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect-owner", help="inspect a wallet owner across configured chains")
    inspect_parser.add_argument("--config", required=True)
    inspect_parser.add_argument("--owner", required=True)
    inspect_parser.add_argument("--chain-id", type=int)
    inspect_parser.set_defaults(handler=command_inspect_owner)

    poll_parser = subparsers.add_parser("poll", help="evaluate watcher trigger decisions")
    poll_parser.add_argument("--config", required=True)
    poll_parser.add_argument("--execute", action="store_true")
    poll_parser.set_defaults(handler=command_poll)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
