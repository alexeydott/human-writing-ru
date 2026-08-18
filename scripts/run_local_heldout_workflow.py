#!/usr/bin/env python3
"""Run the GitHub held-out workflow locally against data/ corpora."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data"
CHECKS = (
    ("scripts/validate_skill.py",),
    ("scripts/validate_eval_design.py",),
    ("tests/test_ablation_v3.py",),
    ("tests/test_edit_integrity.py",),
    ("tests/test_external_gate_runner.py",),
)


def local_environment() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    if not (env.get("GITHUB_TOKEN") or env.get("GH_TOKEN")) and shutil.which("gh"):
        token = subprocess.run(
            ["gh", "auth", "token"], cwd=ROOT, text=True,
            capture_output=True, check=False,
        )
        if token.returncode == 0 and token.stdout.strip():
            env["GITHUB_TOKEN"] = token.stdout.strip()
            print("Using the current gh credential for GitHub API acquisition.", flush=True)
    return env


def run(command: list[str], env: dict[str, str]) -> int:
    print("+", subprocess.list2cmdline(command), flush=True)
    return subprocess.run(command, cwd=ROOT, env=env).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the held-out GitHub Actions workflow locally")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--annotations", type=Path, default=None)
    parser.add_argument("--skip-checks", action="store_true")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--source-process-timeout", type=float, default=300.0)
    args = parser.parse_args()

    data = args.data_dir.expanduser().resolve()
    output = (args.output_dir or (data / "heldout-work")).expanduser().resolve()
    env = local_environment()
    if not args.skip_checks:
        for parts in CHECKS:
            code = run([sys.executable, *parts], env)
            if code:
                return code
    command = [
        sys.executable,
        "scripts/run_external_heldout_gate.py",
        "--output-dir", str(output),
        "--local-corpus-root", str(data),
        "--timeout", str(args.timeout),
        "--source-process-timeout", str(args.source_process_timeout),
    ]
    if args.annotations is not None:
        command.extend(["--annotations", str(args.annotations.expanduser().resolve())])
    code = run(command, env)
    states = {
        0: "evidence and adjudication stages complete; explicit policy review still required",
        3: "profile-size stage incomplete",
        6: "profile-size stage passed; v3 evidence incomplete",
        7: "v3 evidence passed; natural-alert adjudication required",
    }
    print(f"held-out workflow exit={code}: {states.get(code, 'pipeline failure')}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
