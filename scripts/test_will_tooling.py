#!/usr/bin/env python3
"""Unit tests for the Agentic Wallet will helper scripts."""

from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import will_calldata
import will_watcher


class WillCalldataTests(unittest.TestCase):
    def test_known_selectors_match_ethereum_conventions(self) -> None:
        self.assertEqual(will_calldata.function_selector("approve(address,uint256)").hex(), "095ea7b3")
        self.assertEqual(will_calldata.function_selector("transferFrom(address,address,uint256)").hex(), "23b872dd")
        self.assertEqual(will_calldata.function_selector("balanceOf(address)").hex(), "70a08231")
        self.assertEqual(will_calldata.function_selector("allowance(address,address)").hex(), "dd62ed3e")

    def test_encode_approve_uses_max_uint256(self) -> None:
        payload = will_calldata.build_method_payload(
            "approve",
            argparse.Namespace(spender="0x1111111111111111111111111111111111111111", amount="max"),
        )
        self.assertTrue(payload.startswith("0x095ea7b3"))

    def test_decode_address_array_round_trip(self) -> None:
        encoded = will_calldata.abi_encode(
            ("address[]",),
            (["0x1111111111111111111111111111111111111111", "0x2222222222222222222222222222222222222222"],),
        )
        decoded = will_calldata.decode_address_array("0x" + encoded.hex())
        self.assertEqual(
            decoded,
            ["0x1111111111111111111111111111111111111111", "0x2222222222222222222222222222222222222222"],
        )

    def test_decode_will_config(self) -> None:
        words = [
            bytes.fromhex("00" * 12 + "11" * 20),
            bytes.fromhex("00" * 12 + "22" * 20),
            (100).to_bytes(32, "big"),
            (200).to_bytes(32, "big"),
            (1800).to_bytes(32, "big"),
            (900).to_bytes(32, "big"),
            bytes.fromhex("00" * 12 + "33" * 20),
            (1).to_bytes(32, "big"),
            (300).to_bytes(32, "big"),
            bytes.fromhex("44" * 32),
        ]
        config = will_calldata.decode_will_config("0x" + b"".join(words).hex())
        self.assertEqual(config.owner, "0x" + "11" * 20)
        self.assertEqual(config.beneficiary, "0x" + "22" * 20)
        self.assertEqual(config.status_label, "Triggered")
        self.assertEqual(config.deadline, 300)


class WatcherDecisionTests(unittest.TestCase):
    def test_trigger_when_deadline_reached_and_inactive(self) -> None:
        inspection = will_watcher.WillInspection(
            chain_id=56,
            chain_name="BNB Chain",
            factory_address="0x" + "ab" * 20,
            owner="0x" + "01" * 20,
            will_contract="0x" + "02" * 20,
            status=0,
            status_label="Active",
            beneficiary="0x" + "03" * 20,
            trigger_after_seconds=1_200,
            monitor_window_seconds=600,
            deadline=1_000,
            deadline_iso="1970-01-01T00:16:40+00:00",
            created_at=10,
            last_trigger_update_at=20,
            watcher="0x" + "04" * 20,
            claimable=False,
            activity_proof_ref="0x" + "00" * 32,
            authorized_tokens=[],
            allowances=[],
            approval_complete=True,
        )
        activity = will_watcher.ActivityWindow(active=False, activity_ref="0x" + "55" * 32, records=[])
        decision = will_watcher.evaluate_trigger(inspection, now_ts=1_001, activity=activity)
        self.assertTrue(decision.should_trigger)

    def test_no_trigger_when_activity_exists(self) -> None:
        inspection = will_watcher.WillInspection(
            chain_id=56,
            chain_name="BNB Chain",
            factory_address="0x" + "ab" * 20,
            owner="0x" + "01" * 20,
            will_contract="0x" + "02" * 20,
            status=0,
            status_label="Active",
            beneficiary="0x" + "03" * 20,
            trigger_after_seconds=1_200,
            monitor_window_seconds=600,
            deadline=1_000,
            deadline_iso="1970-01-01T00:16:40+00:00",
            created_at=10,
            last_trigger_update_at=20,
            watcher="0x" + "04" * 20,
            claimable=False,
            activity_proof_ref="0x" + "00" * 32,
            authorized_tokens=[],
            allowances=[],
            approval_complete=True,
        )
        activity = will_watcher.ActivityWindow(active=True, activity_ref="window-active", records=[{"id": "tx-1"}])
        decision = will_watcher.evaluate_trigger(inspection, now_ts=1_001, activity=activity)
        self.assertFalse(decision.should_trigger)
        self.assertIn("activity", decision.reason)

if __name__ == "__main__":
    unittest.main()
