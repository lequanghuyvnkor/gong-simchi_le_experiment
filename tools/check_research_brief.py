"""Check the brief's audit table against saved JSON, without rerunning notebooks.

Python 3.10+, standard library only. --print-table prints the current source
table for an intentional document update; it never writes files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results/replication_audit/audit_results.json"
BRIEF = ROOT / "docs/research_direction_d.md"
START = "<!-- audit-evidence:start -->"
END = "<!-- audit-evidence:end -->"
CLAIMS = (
    ("Synthetic: số thời điểm", "runs.synthetic.T", "d"),
    ("Synthetic: chi phí trung bình bộ học", "runs.synthetic.learner.mean", ".5f"),
    ("Synthetic: chi phí trung bình policy DP notebook", "runs.synthetic.author_DP_policy_realized_cost.mean", ".5f"),
    ("Synthetic: chi phí trung bình policy khả thi đối chiếu", "runs.synthetic.candidate_feasible_policy.mean", ".5f"),
    ("Rossmann: số thời điểm", "runs.rossmann.T", "d"),
    ("Rossmann: tổng chi phí bộ học", "runs.rossmann.learner.total", ".0f"),
    ("Rossmann: tổng chi phí vector mang nhãn near_OPT", "runs.rossmann.near_OPT_vector.total", ".0f"),
    ("Rossmann: tổng chi phí sau đổi chỉ số episode", "runs.rossmann_episode_start_sensitivity.learner.total", ".0f"),
)


def lookup(data: dict, key: str):
    value = data
    for part in key.split("."):
        value = value[part]
    return value


def table(data: dict) -> str:
    lines = ["| Chỉ tiêu | Giá trị | Trường JSON nguồn |", "| --- | ---: | --- |"]
    for label, key, spec in CLAIMS:
        value = format(lookup(data, key), spec)
        link = f"[`{key}`](../results/replication_audit/audit_results.json)"
        lines.append(f"| {label} | {value} | {link} |")
    return "\n".join(lines)


def check(data: dict, brief: str) -> None:
    if brief.count(START) != 1 or brief.count(END) != 1:
        raise ValueError("Expected exactly one audit evidence block")
    actual = brief.split(START)[1].split(END)[0].strip()
    if actual != table(data):
        raise ValueError("Brief table differs from saved audit JSON; inspect sources before updating")
    for run in ("synthetic", "rossmann", "rossmann_episode_start_sensitivity"):
        if data["runs"][run]["status"] != "completed":
            raise ValueError(f"Saved run is not completed: {run}")
    for name, item in data["inputs"].items():
        if not item["unchanged"] or item["sha256"] != item["sha256_after"]:
            raise ValueError(f"Saved source-integrity check failed: {name}")
    for key in ("runs.synthetic.learner", "runs.synthetic.author_DP_policy_realized_cost",
                "runs.rossmann.learner", "runs.rossmann.near_OPT_vector",
                "runs.rossmann_episode_start_sensitivity.learner"):
        metric = lookup(data, key)
        if metric["n"] <= 0 or not math.isclose(metric["total"] / metric["n"], metric["mean"],
                                               rel_tol=1e-10, abs_tol=1e-10):
            raise ValueError(f"Inconsistent saved cost arithmetic: {key}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-table", action="store_true")
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error("Python 3.10 or newer is required")
    try:
        raw = SOURCE.read_bytes()
        data = json.loads(raw)
        if args.print_table:
            print(table(data))
            return 0
        check(data, BRIEF.read_text(encoding="utf-8"))
    except (OSError, KeyError, TypeError, ValueError) as exc:
        parser.exit(1, f"Evidence check failed: {exc}\n")
    print(json.dumps({
        "status": "passed",
        "scope": "Document-to-snapshot consistency only; no notebook or theorem verification",
        "python": platform.python_version(),
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "table_metrics_checked": len(CLAIMS),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
