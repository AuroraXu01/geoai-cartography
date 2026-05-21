#!/usr/bin/env python3
"""Batch render maps from a JSON job file."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
RENDER_MAP = SCRIPT_DIR / "render_map.py"


def load_jobs(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        jobs = data.get("jobs")
    else:
        jobs = data
    if not isinstance(jobs, list) or not jobs:
        raise SystemExit("Batch config must be a non-empty list or an object with a non-empty 'jobs' list.")
    return jobs


def job_to_args(job: dict, base_dir: Path) -> list[str]:
    if "input" not in job or "output" not in job:
        raise SystemExit("Each batch job requires 'input' and 'output'.")
    args = [sys.executable, str(RENDER_MAP), str((base_dir / job["input"]).resolve() if not Path(job["input"]).is_absolute() else Path(job["input"]))]
    args.extend(["--output", str((base_dir / job["output"]).resolve() if not Path(job["output"]).is_absolute() else Path(job["output"]) )])
    for key, value in job.items():
        if key in {"input", "output"} or value is None or value is False:
            continue
        option = "--" + key.replace("_", "-")
        if value is True:
            args.append(option)
        elif isinstance(value, list):
            args.extend([option, ",".join(str(v) for v in value)])
        else:
            args.extend([option, str(value)])
    return args


def main() -> int:
    parser = argparse.ArgumentParser(description="Run multiple render_map.py jobs from JSON.")
    parser.add_argument("config", type=Path, help="JSON file containing a jobs list.")
    parser.add_argument("--base-dir", type=Path, help="Resolve relative input/output paths from this directory. Default: config directory.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = args.config.expanduser().resolve()
    base_dir = args.base_dir.expanduser().resolve() if args.base_dir else config.parent
    jobs = load_jobs(config)
    for index, job in enumerate(jobs, start=1):
        command = job_to_args(job, base_dir)
        print(f"[{index}/{len(jobs)}] {' '.join(command)}")
        if not args.dry_run:
            subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
