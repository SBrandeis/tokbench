#!/usr/bin/env bash
# Runs inside the Job, from a tokbench checkout: pin both arms, build, measure, report.
set -Eeuo pipefail

: "${TOKBENCH_AB_BASE:?}" "${TOKBENCH_AB_TIP:?}" "${TOKBENCH_AB_REPO:?}" "${TOKBENCH_UV_VERSION:?}"

command -v uvx >/dev/null || curl -LsSf "https://astral.sh/uv/${TOKBENCH_UV_VERSION}/install.sh" \
  | env UV_INSTALL_DIR=/usr/local/bin sh

python3 hf-jobs/pin_pipeline.py pipeline "${TOKBENCH_AB_TIP}" --repo "${TOKBENCH_AB_REPO}"
python3 hf-jobs/pin_pipeline.py pipeline-base "${TOKBENCH_AB_BASE}" --repo "${TOKBENCH_AB_REPO}"

# Not --locked: the two pins are new to Cargo.lock. Cargo keeps every entry it
# can, and the lockfile it resolved is saved next to the results.
export TOKBENCH_FEATURES=hf-tokenizers,pipeline,pipeline-base
cargo build --release -p tokbench --features "${TOKBENCH_FEATURES}"

export JOB_ID="${JOB_ID:-local-$(date -u +%Y%m%dT%H%M%SZ)}"
output_dir="${TOKBENCH_OUTPUT_DIR:-/outputs}/${JOB_ID}"
mkdir -p "${output_dir}"
cp Cargo.lock "${output_dir}/Cargo.lock"

# hf-tokenizers is there to verify the ids; the comparator must stay out of the engine list.
TOKBENCH_SKIP_BUILD=1 \
TOKBENCH_MEASURE=encode \
TOKBENCH_ENGINES=hf-tokenizers,pipeline \
TOKBENCH_COMPARE_TO=pipeline-base \
  bash hf-jobs/run.sh

python3 hf-jobs/ab_report.py "${output_dir}"/run-*.json | tee "${output_dir}/ab-report.txt"
