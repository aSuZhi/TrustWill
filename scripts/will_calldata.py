#!/usr/bin/env python3
"""Deterministic ABI encoding helpers for the Agentic Wallet will contracts."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Sequence

MASK_64 = (1 << 64) - 1
MAX_UINT256 = (1 << 256) - 1

ROTATION_OFFSETS = (
    (0, 36, 3, 41, 18),
    (1, 44, 10, 45, 2),
    (62, 6, 43, 15, 61),
    (28, 55, 25, 21, 56),
    (27, 20, 39, 8, 14),
)

ROUND_CONSTANTS = (
    0x0000000000000001,
    0x0000000000008082,
    0x800000000000808A,
    0x8000000080008000,
    0x000000000000808B,
    0x0000000080000001,
    0x8000000080008081,
    0x8000000000008009,
    0x000000000000008A,
    0x0000000000000088,
    0x0000000080008009,
    0x000000008000000A,
    0x000000008000808B,
    0x800000000000008B,
    0x8000000000008089,
    0x8000000000008003,
    0x8000000000008002,
    0x8000000000000080,
    0x000000000000800A,
    0x800000008000000A,
    0x8000000080008081,
    0x8000000000008080,
    0x0000000080000001,
    0x8000000080008008,
)

METHOD_SPECS = {
    "create-will": ("createWill(address,uint256,address)", ("address", "uint256", "address")),
    "register-tokens": ("registerAuthorizedTokens(address[])", ("address[]",)),
    "update-beneficiary": ("updateBeneficiary(address)", ("address",)),
    "update-trigger-seconds": ("updateTriggerAfterSeconds(uint256)", ("uint256",)),
    "update-trigger-days": ("updateTriggerAfterDays(uint256)", ("uint256",)),
    "add-tokens": ("addAuthorizedTokens(address[])", ("address[]",)),
    "cancel-will": ("cancelWill()", ()),
    "mark-triggered": ("markTriggered(bytes32)", ("bytes32",)),
    "claim": ("claim(address[])", ("address[]",)),
    "approve": ("approve(address,uint256)", ("address", "uint256")),
    "allowance": ("allowance(address,address)", ("address", "address")),
    "balance-of": ("balanceOf(address)", ("address",)),
    "owner-to-will": ("ownerToWill(address)", ("address",)),
    "get-will-config": ("getWillConfig()", ()),
    "get-authorized-tokens": ("getAuthorizedTokens()", ()),
}

STATUS_LABELS = {
    0: "Active",
    1: "Triggered",
    2: "Cancelled",
    3: "Claimed",
}


def _rotl64(value: int, bits: int) -> int:
    return ((value << bits) & MASK_64) | (value >> (64 - bits))


def keccak256(message: bytes) -> bytes:
    state = [0] * 25
    rate = 136
    padded = bytearray(message)
    padded.append(0x01)
    while len(padded) % rate != rate - 1:
        padded.append(0)
    padded.append(0x80)

    for start in range(0, len(padded), rate):
        block = padded[start : start + rate]
        for offset, byte in enumerate(block):
            state[offset // 8] ^= byte << (8 * (offset % 8))
        _keccak_f1600(state)

    output = bytearray()
    while len(output) < 32:
        for offset in range(rate):
            output.append((state[offset // 8] >> (8 * (offset % 8))) & 0xFF)
            if len(output) == 32:
                return bytes(output)
        _keccak_f1600(state)
    raise AssertionError("unreachable")


def _keccak_f1600(state: list[int]) -> None:
    for round_constant in ROUND_CONSTANTS:
        c = [state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rotl64(c[(x + 1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                state[x + 5 * y] ^= d[x]

        b = [0] * 25
        for x in range(5):
            for y in range(5):
                new_x = y
                new_y = (2 * x + 3 * y) % 5
                b[new_x + 5 * new_y] = _rotl64(state[x + 5 * y], ROTATION_OFFSETS[x][y])

        for x in range(5):
            for y in range(5):
                state[x + 5 * y] = b[x + 5 * y] ^ ((~b[((x + 1) % 5) + 5 * y]) & b[((x + 2) % 5) + 5 * y])

        state[0] ^= round_constant


def normalize_address(value: str) -> str:
    text = value.strip()
    if text.lower().startswith("xko"):
        raise ValueError("XKO address format is not supported for EVM calldata; use the canonical 0x address.")
    if not text.startswith("0x") or len(text) != 42:
        raise ValueError(f"invalid EVM address: {value}")
    int(text[2:], 16)
    return "0x" + text[2:].lower()


def parse_address_list(raw: str) -> list[str]:
    parts = [item.strip() for item in raw.split(",") if item.strip()]
    if not parts:
        raise ValueError("at least one token address is required")
    return [normalize_address(item) for item in parts]


def encode_uint256(value: int) -> bytes:
    if value < 0 or value > MAX_UINT256:
        raise ValueError(f"uint256 out of range: {value}")
    return value.to_bytes(32, byteorder="big")


def encode_address(value: str) -> bytes:
    normalized = normalize_address(value)
    return bytes.fromhex("00" * 12 + normalized[2:])


def encode_bytes32(value: str) -> bytes:
    text = value[2:] if value.startswith("0x") else value
    if len(text) != 64:
        raise ValueError("bytes32 values must be exactly 32 bytes")
    return bytes.fromhex(text)


def encode_single(abi_type: str, value: object) -> bytes:
    if abi_type == "address":
        return encode_address(str(value))
    if abi_type == "uint256":
        return encode_uint256(int(value))
    if abi_type == "bytes32":
        return encode_bytes32(str(value))
    if abi_type == "address[]":
        items = [normalize_address(str(item)) for item in value]
        encoded = [encode_uint256(len(items))]
        encoded.extend(encode_address(item) for item in items)
        return b"".join(encoded)
    raise ValueError(f"unsupported ABI type: {abi_type}")


def is_dynamic(abi_type: str) -> bool:
    return abi_type.endswith("[]")


def abi_encode(types: Sequence[str], values: Sequence[object]) -> bytes:
    if len(types) != len(values):
        raise ValueError("types and values length mismatch")

    heads: list[bytes] = []
    tails: list[bytes] = []
    offset = 32 * len(types)
    for abi_type, value in zip(types, values):
        if is_dynamic(abi_type):
            encoded_tail = encode_single(abi_type, value)
            heads.append(encode_uint256(offset))
            tails.append(encoded_tail)
            offset += len(encoded_tail)
        else:
            heads.append(encode_single(abi_type, value))
    return b"".join(heads + tails)


def function_selector(signature: str) -> bytes:
    return keccak256(signature.encode("utf-8"))[:4]


def encode_call(signature: str, types: Sequence[str], values: Sequence[object]) -> str:
    return "0x" + (function_selector(signature) + abi_encode(types, values)).hex()


def _ensure_bytes(data_hex: str) -> bytes:
    text = data_hex[2:] if data_hex.startswith("0x") else data_hex
    if len(text) % 2 != 0:
        raise ValueError("hex payload length must be even")
    return bytes.fromhex(text)


def decode_uint256(data_hex: str) -> int:
    data = _ensure_bytes(data_hex)
    if len(data) < 32:
        raise ValueError("uint256 payload must contain at least 32 bytes")
    return int.from_bytes(data[:32], "big")


def decode_address(data_hex: str) -> str:
    data = _ensure_bytes(data_hex)
    if len(data) < 32:
        raise ValueError("address payload must contain at least 32 bytes")
    return "0x" + data[12:32].hex()


def decode_address_array(data_hex: str) -> list[str]:
    data = _ensure_bytes(data_hex)
    if len(data) < 64:
        return []
    offset = int.from_bytes(data[:32], "big")
    if offset + 32 > len(data):
        raise ValueError("invalid dynamic array offset")
    length = int.from_bytes(data[offset : offset + 32], "big")
    items: list[str] = []
    cursor = offset + 32
    for _ in range(length):
        chunk = data[cursor : cursor + 32]
        if len(chunk) != 32:
            raise ValueError("unexpected end of address array")
        items.append("0x" + chunk[12:32].hex())
        cursor += 32
    return items


@dataclass(frozen=True)
class WillConfig:
    owner: str
    beneficiary: str
    created_at: int
    last_trigger_update_at: int
    trigger_after_seconds: int
    monitor_window_seconds: int
    watcher: str
    status: int
    deadline: int
    activity_proof_ref: str

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, f"Unknown({self.status})")


def decode_will_config(data_hex: str) -> WillConfig:
    data = _ensure_bytes(data_hex)
    if len(data) < 320:
        raise ValueError("getWillConfig payload must contain 10 words")
    words = [data[index : index + 32] for index in range(0, 320, 32)]
    return WillConfig(
        owner="0x" + words[0][12:].hex(),
        beneficiary="0x" + words[1][12:].hex(),
        created_at=int.from_bytes(words[2], "big"),
        last_trigger_update_at=int.from_bytes(words[3], "big"),
        trigger_after_seconds=int.from_bytes(words[4], "big"),
        monitor_window_seconds=int.from_bytes(words[5], "big"),
        watcher="0x" + words[6][12:].hex(),
        status=int.from_bytes(words[7], "big"),
        deadline=int.from_bytes(words[8], "big"),
        activity_proof_ref="0x" + words[9].hex(),
    )


def parse_amount(raw: str) -> int:
    if raw.lower() == "max":
        return MAX_UINT256
    return int(raw, 10)


def parse_trigger_seconds(args: argparse.Namespace) -> int:
    if args.seconds is not None:
        return int(args.seconds)
    if args.minutes is not None:
        return int(args.minutes) * 60
    if args.hours is not None:
        return int(args.hours) * 3600
    if args.days is not None:
        return int(args.days) * 86400
    raise ValueError("missing trigger duration; provide one of --seconds, --minutes, --hours, or --days")


def build_method_payload(method: str, args: argparse.Namespace) -> str:
    signature, types = METHOD_SPECS[method]
    if method == "create-will":
        values = (args.beneficiary, parse_trigger_seconds(args), args.watcher)
    elif method in {"register-tokens", "add-tokens", "claim"}:
        values = (parse_address_list(args.tokens),)
    elif method == "update-beneficiary":
        values = (args.beneficiary,)
    elif method == "update-trigger-seconds":
        values = (parse_trigger_seconds(args),)
    elif method == "update-trigger-days":
        values = (args.days,)
    elif method == "cancel-will":
        values = ()
    elif method == "mark-triggered":
        values = (args.activity_ref,)
    elif method == "approve":
        values = (args.spender, parse_amount(args.amount))
    elif method == "allowance":
        values = (args.owner, args.spender)
    elif method == "balance-of":
        values = (args.owner,)
    elif method == "owner-to-will":
        values = (args.owner,)
    elif method in {"get-will-config", "get-authorized-tokens"}:
        values = ()
    else:
        raise ValueError(f"unsupported method: {method}")
    return encode_call(signature, types, values)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    selector_parser = subparsers.add_parser("selector", help="print the selector for a function signature")
    selector_parser.add_argument("signature")

    encode_parser = subparsers.add_parser("encode", help="encode a supported calldata payload")
    encode_parser.add_argument("method", choices=sorted(METHOD_SPECS))
    encode_parser.add_argument("--beneficiary")
    encode_parser.add_argument("--seconds", type=int)
    encode_parser.add_argument("--minutes", type=int)
    encode_parser.add_argument("--hours", type=int)
    encode_parser.add_argument("--days", type=int)
    encode_parser.add_argument("--watcher")
    encode_parser.add_argument("--tokens")
    encode_parser.add_argument("--activity-ref")
    encode_parser.add_argument("--spender")
    encode_parser.add_argument("--amount")
    encode_parser.add_argument("--owner")

    decode_parser = subparsers.add_parser("decode", help="decode supported return payloads")
    decode_parser.add_argument("kind", choices=("address", "uint256", "address-array", "will-config"))
    decode_parser.add_argument("data")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "selector":
        print("0x" + function_selector(args.signature).hex())
        return 0

    if args.command == "encode":
        payload = build_method_payload(args.method, args)
        signature = METHOD_SPECS[args.method][0]
        print(json.dumps({"method": args.method, "signature": signature, "data": payload}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "decode":
        if args.kind == "address":
            decoded: object = decode_address(args.data)
        elif args.kind == "uint256":
            decoded = decode_uint256(args.data)
        elif args.kind == "address-array":
            decoded = decode_address_array(args.data)
        else:
            config = decode_will_config(args.data)
            decoded = {
                "owner": config.owner,
                "beneficiary": config.beneficiary,
                "created_at": config.created_at,
                "last_trigger_update_at": config.last_trigger_update_at,
                "trigger_after_seconds": config.trigger_after_seconds,
                "monitor_window_seconds": config.monitor_window_seconds,
                "watcher": config.watcher,
                "status": config.status,
                "status_label": config.status_label,
                "deadline": config.deadline,
                "activity_proof_ref": config.activity_proof_ref,
            }
        print(json.dumps(decoded, ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
