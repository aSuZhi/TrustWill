#!/usr/bin/env python3
"""Adapter that derives Agentic Wallet activity from onchainos wallet history."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from typing import Any


def run_json(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or f"command failed: {' '.join(command)}")
    return json.loads(completed.stdout)


def collect_addresses(payload: dict[str, Any]) -> set[str]:
    data = payload.get("data") or {}
    addresses: set[str] = set()
    for key in ("xlayer", "evm", "solana"):
        for item in data.get(key) or []:
            address = item.get("address")
            if isinstance(address, str):
                addresses.add(address.lower())
    return addresses


def collect_history_records(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    records: list[dict[str, Any]] = []
    cursor = ""
    for page in payload.get("data") or []:
        cursor = page.get("cursor") or ""
        records.extend(page.get("orderList") or [])
    return records, cursor


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--chain-id", required=True)
    parser.add_argument("--begin-ms", required=True)
    parser.add_argument("--end-ms", required=True)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--onchainos-bin", default="onchainos")
    args = parser.parse_args()

    owner = args.owner.lower()
    addresses_payload = run_json([args.onchainos_bin, "wallet", "addresses", "--chain", str(args.chain_id)])
    current_addresses = collect_addresses(addresses_payload)
    if owner not in current_addresses:
        raise RuntimeError(
            f"owner {args.owner} does not match the currently selected Agentic Wallet account on chain {args.chain_id}"
        )

    all_records: list[dict[str, Any]] = []
    page_cursor = ""
    page_count = 0

    while page_count < args.max_pages:
        command = [
            args.onchainos_bin,
            "wallet",
            "history",
            "--chain",
            str(args.chain_id),
            "--begin",
            str(args.begin_ms),
            "--end",
            str(args.end_ms),
            "--limit",
            str(args.limit),
        ]
        if page_cursor:
            command.extend(["--page-num", page_cursor])

        history_payload = run_json(command)
        records, next_cursor = collect_history_records(history_payload)
        all_records.extend(records)
        page_count += 1
        if not next_cursor:
            break
        page_cursor = next_cursor

    active_records = []
    for record in all_records:
        sender = str(record.get("from") or "").lower()
        tx_hash = record.get("txHash")
        if sender == owner and tx_hash:
            active_records.append(
                {
                    "txHash": tx_hash,
                    "txTime": record.get("txTime"),
                    "direction": record.get("direction"),
                    "coinSymbol": record.get("coinSymbol"),
                    "chainSymbol": record.get("chainSymbol"),
                }
            )

    digest_source = "|".join(
        [
            args.owner.lower(),
            str(args.chain_id),
            str(args.begin_ms),
            str(args.end_ms),
            ",".join(record["txHash"] for record in active_records),
        ]
    )
    activity_ref = "0x" + hashlib.sha256(digest_source.encode("utf-8")).hexdigest()

    print(
        json.dumps(
            {
                "active": bool(active_records),
                "activity_ref": activity_ref,
                "records": active_records,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
