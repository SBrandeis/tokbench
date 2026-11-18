#!/usr/bin/env python3
"""Report tip/base encode throughput from the runs of one A/B Job."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

Cell = tuple[str, str]


def paired_ratios(
    reports: list[dict], tip: str, base: str
) -> tuple[dict[Cell, list[float]], set[Cell]]:
    """One tip/base ratio per run for each cell, and the cells left out.

    A cell is left out when either arm, in any run, has no throughput or ids
    that differ from the reference.
    """
    ratios: dict[Cell, list[float]] = {}
    excluded: set[Cell] = set()
    for report in reports:
        for run in report["runs"]:
            meta = run["dataset_metadata"]
            cell = (meta["model"], meta["corpus"])
            arms = {r["tokenizer_name"]: r for r in run["results"]}
            measured = [
                arms[name]["mbps"]
                for name in (tip, base)
                if name in arms and arms[name].get("verified") is True and arms[name].get("mbps")
            ]
            if len(measured) == 2:
                ratios.setdefault(cell, []).append(measured[0] / measured[1])
            else:
                excluded.add(cell)
    for cell in excluded:
        ratios.pop(cell, None)
    return ratios, excluded


def spread(values: list[float]) -> str:
    return f"{statistics.median(values):.3f}  [{min(values):.3f} - {max(values):.3f}]"


def render(ratios: dict[Cell, list[float]], excluded: set[Cell], tip: str, base: str) -> str:
    runs = min(map(len, ratios.values()), default=0)
    lines = [f"{tip} / {base}, encode MB/s, median [min - max] of {runs} runs", ""]
    rows = [(f"{model} {corpus}", values) for (model, corpus), values in sorted(ratios.items())]
    if ratios:
        per_run = [
            statistics.geometric_mean(values[i] for values in ratios.values())
            for i in range(runs)
        ]
        rows.append((f"geomean of {len(ratios)} cells", per_run))
    width = max((len(label) for label, _ in rows), default=0) + 2
    lines += [f"{label:<{width}}{spread(values)}" for label, values in rows]
    if excluded:
        lines += ["", "no ratio (unsupported, or ids differ from the reference):"]
        lines += [f"  {model} {corpus}" for model, corpus in sorted(excluded)]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path, help="run-*.json of one Job")
    parser.add_argument("--tip", default="pipeline")
    parser.add_argument("--base", default="pipeline-base")
    args = parser.parse_args()
    reports = [json.loads(path.read_text()) for path in args.reports]
    print(render(*paired_ratios(reports, args.tip, args.base), args.tip, args.base))


if __name__ == "__main__":
    main()
