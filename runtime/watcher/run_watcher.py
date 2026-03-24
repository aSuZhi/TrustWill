#!/usr/bin/env python3
"""Wrapper for the will watcher with a friendlier entrypoint."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--python-bin", default=sys.executable)
    args = parser.parse_args()
    runtime_root = Path(__file__).resolve().parents[1]
    skill_root = runtime_root.parent
    watcher_script = skill_root / "scripts" / "will_watcher.py"

    command = [
        args.python_bin,
        str(watcher_script),
        "poll",
        "--config",
        args.config,
    ]
    if args.execute:
        command.append("--execute")

    completed = subprocess.run(command, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
