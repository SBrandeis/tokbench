#!/usr/bin/env python3
"""Pin a pipeline engine (pipeline or pipeline-base) to a tokenizers commit."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHA = re.compile(r"[0-9a-f]{40}")


def pin(text: str, rev: str, repo: str) -> str:
    text = SHA.sub(rev, text)
    text = re.sub(r"tokenizers @ [0-9a-f]{8}", f"tokenizers @ {rev[:8]}", text)
    return re.sub(r"https://github\.com/[\w.-]+/[\w.-]+", f"https://github.com/{repo}", text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=("pipeline", "pipeline-base"))
    parser.add_argument("rev", help="Full tokenizers commit SHA")
    parser.add_argument("--repo", default="huggingface/tokenizers", help="GitHub repo holding the commit")
    args = parser.parse_args()
    if not SHA.fullmatch(args.rev):
        raise SystemExit("rev must be a full 40-character commit SHA")
    for name in ("Cargo.toml", "src/lib.rs"):
        path = ROOT / "engines" / args.engine / name
        path.write_text(pin(path.read_text(), args.rev, args.repo))


if __name__ == "__main__":
    main()
