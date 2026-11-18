#!/usr/bin/env python3
"""Submit an A/B of two tokenizers commits as one Hugging Face Job.

The Job clones tokbench at the local HEAD, pins the `pipeline` engine to the
tip and `pipeline-base` to the base, builds both into one binary and measures
encode on the same host. Passing the same commit twice is the A/A control:
its ratios are the noise floor of the Job.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess

from publish_space import HUB_VERSION, RUST_IMAGE, UV_IMAGE

INPUT_REPO = "hf-internal-testing/tokenizers-test-data"
CORPORA_REPO = "huggingface/tokbench-corpora"
UV_VERSION = UV_IMAGE.split(":")[1].split("@")[0]


def resolve(repo: str, ref: str) -> str:
    """Full SHA of a branch, tag, `pull/N/head` or short SHA on GitHub."""
    import httpx  # ships with huggingface_hub, and brings its own CA bundle

    response = httpx.get(
        f"https://api.github.com/repos/{repo}/commits/{ref}",
        headers={"Accept": "application/vnd.github.sha"},
    )
    if response.status_code != 200:
        raise SystemExit(f"cannot resolve {ref} in {repo}: HTTP {response.status_code}")
    return response.text.strip()


def job_spec(args, *, tokbench_rev, base, tip, input_rev, corpora_rev) -> dict:
    return {
        "image": RUST_IMAGE,
        "command": [
            "bash",
            "-c",
            f"git clone -q https://github.com/{args.tokbench_repo}.git tokbench && cd tokbench "
            f"&& git checkout -q --detach {tokbench_rev} && exec bash hf-jobs/ab.sh",
        ],
        "env": {
            "TOKBENCH_AB_BASE": base,
            "TOKBENCH_AB_TIP": tip,
            "TOKBENCH_AB_REPO": args.repo,
            "TOKBENCH_SOURCE_REVISION": tokbench_rev,
            "TOKBENCH_INPUT_REVISION": input_rev,
            "TOKBENCH_CORPORA_REVISION": corpora_rev,
            "TOKBENCH_MODELS": args.models or "",
            "TOKBENCH_RUNS": str(args.runs),
            "TOKBENCH_REPS": str(args.reps),
            "TOKBENCH_UV_VERSION": UV_VERSION,
            "HF_HUB_VERSION": HUB_VERSION,
            "HF": f"uvx --from huggingface_hub=={HUB_VERSION} hf",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="tokenizers commit, branch, tag or pull/N/head")
    parser.add_argument("--tip", required=True, help="Same forms as --base")
    parser.add_argument("--repo", default="huggingface/tokenizers", help="GitHub repo holding both commits")
    parser.add_argument("--tokbench-repo", default="huggingface/tokbench", help="GitHub repo holding the local HEAD")
    parser.add_argument("--models", help="Comma-separated model allowlist; default is the Makefile's")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--reps", type=int, default=5)
    parser.add_argument("--input-revision", default="main", help=f"Revision of {INPUT_REPO}")
    parser.add_argument("--corpora-revision", default="main", help=f"Revision of {CORPORA_REPO}")
    parser.add_argument("--bucket", help="HF Storage Bucket for the reports; without it they stay in the Job logs")
    parser.add_argument("--namespace")
    parser.add_argument("--flavor", default="cpu-performance")
    parser.add_argument("--timeout", default="2h")
    parser.add_argument("--dry-run", action="store_true", help="Print the Job instead of submitting it")
    args = parser.parse_args()

    from huggingface_hub import HfApi, Volume, get_token, run_job

    if subprocess.run(("git", "status", "--porcelain", "--untracked-files=no"),
                      check=True, capture_output=True, text=True).stdout:
        raise SystemExit("the Job clones a commit: commit and push the local changes first")
    head = subprocess.run(("git", "rev-parse", "HEAD"), check=True, capture_output=True, text=True).stdout.strip()
    api = HfApi()
    spec = job_spec(
        args,
        tokbench_rev=resolve(args.tokbench_repo, head),
        base=resolve(args.repo, args.base),
        tip=resolve(args.repo, args.tip),
        input_rev=api.dataset_info(INPUT_REPO, revision=args.input_revision).sha,
        corpora_rev=api.dataset_info(CORPORA_REPO, revision=args.corpora_revision).sha,
    )
    if args.dry_run:
        print(json.dumps(spec, indent=2))
        return

    job = run_job(
        **spec,
        flavor=args.flavor,
        namespace=args.namespace,
        timeout=args.timeout,
        secrets={"HF_TOKEN": os.environ.get("HF_TOKEN") or get_token()},
        volumes=[Volume(type="bucket", source=args.bucket, mount_path="/outputs")] if args.bucket else None,
        labels={
            "name": "tokbench-ab",
            "project": "tokbench",
            "base": spec["env"]["TOKBENCH_AB_BASE"][:12],
            "tip": spec["env"]["TOKBENCH_AB_TIP"][:12],
        },
    )
    print(job.url)
    print(f"job id: {job.id}")


if __name__ == "__main__":
    main()
