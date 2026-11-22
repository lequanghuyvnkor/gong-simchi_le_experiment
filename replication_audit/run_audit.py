"""Run a read-only audit of the publisher's supplementary notebooks.

Usage:
    python replication_audit/run_audit.py --package-dir PATH_TO_EXTRACTED_PACKAGE

The script executes notebook code cells in isolated namespaces. It disables plot
writes, seeds only the synthetic example, and never edits the supplied files.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import platform
import sys
import time
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "replication_audit"
EXPECTED = {
    "final_synthetic.ipynb": "a34719ac8173f546dd55755233b151eb47020ee6104c8fc85bcad69b077e83b4",
    "final_rossman.ipynb": "95fff51814034324257db4e808a6e78516ccb4618467d4a002c6e160939230dd",
    "rossman.csv": "f6e4597c142d7d909a13d53b68a8e85c00b9a4c7b5ff40adbb37d6829cc1f4cc",
    "readme.pdf": "42c7b0b3cb705959e7c284cbf56f13e111ff83f7a57deeadfd77f073e9443dd2",
}
TIMING_OLD = "shift_HQL_update(w,episode, phase, start_x, start_t, Q, V,A, 1)"
TIMING_NEW = "shift_HQL_update(w,episode, phase, start_x, t-H, Q, V,A, 1)"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def notebook_cells(path: Path) -> list[str]:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    return ["".join(cell.get("source", [])) for cell in notebook["cells"]
            if cell.get("cell_type") == "code" and "".join(cell.get("source", [])).strip()]


@contextlib.contextmanager
def quiet_figures():
    show, savefig = plt.show, plt.savefig
    figure_savefig = matplotlib.figure.Figure.savefig
    plt.show = lambda *args, **kwargs: None
    plt.savefig = lambda *args, **kwargs: None
    matplotlib.figure.Figure.savefig = lambda *args, **kwargs: None
    try:
        yield
    finally:
        plt.show, plt.savefig = show, savefig
        matplotlib.figure.Figure.savefig = figure_savefig


def execute_notebook(path: Path, package_dir: Path, *, synthetic: bool,
                     timing_control: bool = False) -> tuple[dict, str, int, list[str]]:
    namespace: dict = {"__name__": "__main__"}
    output = io.StringIO()
    replacements = 0
    captured_warnings: list[str] = []
    old_cwd = Path.cwd()
    try:
        os.chdir(package_dir)
        with quiet_figures(), contextlib.redirect_stdout(output), warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            for index, source in enumerate(notebook_cells(path)):
                if synthetic and index == 1:
                    namespace["np"].random.seed(0)
                if timing_control:
                    replacements += source.count(TIMING_OLD)
                    source = source.replace(TIMING_OLD, TIMING_NEW)
                exec(compile(source, f"{path.name}:cell{index}", "exec"), namespace)
            captured_warnings = [f"{item.category.__name__}: {item.message}" for item in caught]
    finally:
        os.chdir(old_cwd)
    return namespace, output.getvalue(), replacements, captured_warnings


def positive_cost(values) -> dict:
    array = np.asarray(values, dtype=float)
    return {"n": int(array.size), "total": float(-array.sum()),
            "mean": float(-array.mean())}


def feasible_synthetic_policy(demand, targets) -> dict:
    inventory = 0.0
    total = 0.0
    for t, realized in enumerate(demand):
        order_up_to = max(inventory, targets[t % len(targets)])
        total += abs(order_up_to - realized)
        inventory = max(order_up_to - realized, 0.0)
    return {"targets": list(targets), "total": float(total),
            "mean": float(total / len(demand))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-dir", required=True, type=Path,
                        help="Directory containing the official notebooks, rossman.csv and readme.pdf")
    parser.add_argument("--output-dir", type=Path, default=OUT)
    args = parser.parse_args()
    package = args.package_dir.resolve()
    out = args.output_dir.resolve()
    missing = [name for name in EXPECTED if not (package / name).is_file()]
    if missing:
        raise SystemExit("Missing files in supplementary package: " + ", ".join(missing))

    before = {name: sha256(package / name) for name in EXPECTED}
    mismatches = {name: {"expected": EXPECTED[name], "actual": before[name]}
                  for name in EXPECTED if EXPECTED[name] != before[name]}
    if mismatches:
        raise SystemExit("Input SHA-256 mismatch; refusing to label this the audited package: "
                         + json.dumps(mismatches, indent=2))

    started = time.perf_counter()
    synthetic_ns, synthetic_stdout, _, synthetic_warnings = execute_notebook(
        package / "final_synthetic.ipynb", package, synthetic=True)
    ross_ns, ross_stdout, _, ross_warnings = execute_notebook(
        package / "final_rossman.ipynb", package, synthetic=False)
    timing_ns, timing_stdout, timing_replacements, timing_warnings = execute_notebook(
        package / "final_rossman.ipynb", package, synthetic=False, timing_control=True)
    if timing_replacements != 1:
        raise RuntimeError(f"Expected one episode-start call to replace, found {timing_replacements}")

    targets = [9, 4, 1, 0, 6]
    evaluated_demand = synthetic_ns["demand"][:synthetic_ns["T"]]
    synthetic_control = feasible_synthetic_policy(evaluated_demand, targets)
    dp_policy = [int(v) for v in synthetic_ns["opt_policy"]]
    dp_targets = [float(synthetic_ns["action_space"][v]) for v in dp_policy]
    synthetic_dp_check = positive_cost(synthetic_ns["opt_cost"])
    synthetic_result = {
        "status": "completed",
        "seed": 0,
        "T": int(synthetic_ns["T"]),
        "H": int(synthetic_ns["H"]),
        "learner": positive_cost(synthetic_ns["cost_list"]),
        "author_DP_policy_indices": dp_policy,
        "author_DP_policy_targets": dp_targets,
        "author_DP_policy_realized_cost": synthetic_dp_check,
        "candidate_feasible_policy": synthetic_control,
        "stdout": synthetic_stdout,
        "warnings": synthetic_warnings,
    }
    rossman_result = {
        "status": "completed",
        "T": int(ross_ns["T"]),
        "H": int(ross_ns["H"]),
        "learner": positive_cost(ross_ns["original_cost_list"]),
        "expert_advice": positive_cost(ross_ns["cost_list"]),
        "near_OPT_vector": positive_cost(ross_ns["opt_cost"]),
        "best_iid": {"n": int(len(ross_ns["iid_list"])),
                     "mean": float(np.mean(ross_ns["iid_list"]))},
        "stdout": ross_stdout,
        "warnings": ross_warnings,
    }
    timing_result = {
        "status": "completed" if timing_replacements == 1 else "unexpected_replacement_count",
        "replacement_count": timing_replacements,
        "learner": positive_cost(timing_ns["original_cost_list"]),
        "stdout": timing_stdout,
        "warnings": timing_warnings,
    }

    dp_cell = next((cell for cell in notebook_cells(package / "final_synthetic.ipynb")
                    if "def DP()" in cell), "")
    loop_index = dp_cell.find("for k in range(K)")
    assignment_index = dp_cell.find("Q_list=", loop_index)
    mean_index = dp_cell.find("np.mean(Q_list)", loop_index)
    dp_finding = {
        "status": "confirmed_in_supplied_code" if loop_index >= 0 and assignment_index > loop_index and mean_index > assignment_index else "needs_review",
        "evidence": "Inside DP, Q_list is assigned a single sample value inside the k loop; np.mean(Q_list) therefore does not average a collection of K samples.",
        "implication": "The notebook's object labeled opt_policy needs independent benchmark validation before it is treated as a certified lower bound on cost.",
        "independent_same_demand_comparison": {
            "author_DP_policy_mean_cost": synthetic_dp_check["mean"],
            "candidate_feasible_policy_mean_cost": synthetic_control["mean"],
        },
    }
    final_hashes = {name: sha256(package / name) for name in EXPECTED}
    changed_inputs = [name for name in EXPECTED if before[name] != final_hashes[name]]
    if changed_inputs:
        raise RuntimeError("The audit modified input files: " + ", ".join(changed_inputs))
    result = {
        "title": "Read-only replication audit of the publisher's supplementary package",
        "scope": "Executes the supplied notebook cells in fresh namespaces. No source notebook or dataset is edited. Plot display and file writes are disabled. Synthetic demand is seeded to 0.",
        "environment": {"python": sys.version, "platform": platform.platform(),
                        "numpy": np.__version__, "pandas": pd.__version__},
        "inputs": {name: {"bytes": (package / name).stat().st_size,
                          "sha256": before[name], "sha256_after": final_hashes[name],
                          "unchanged": before[name] == final_hashes[name]}
                   for name in EXPECTED},
        "runs": {"synthetic": synthetic_result, "rossmann": rossman_result,
                 "rossmann_episode_start_sensitivity": timing_result},
        "findings": {
            "synthetic_DP_benchmark": dp_finding,
            "episode_start_indexing": {
                "status": timing_result["status"],
                "change": "Pass each episode's actual start index (t-H) to the HQL update instead of reusing the containing block start.",
                "learner_mean_cost": timing_result["learner"]["mean"],
                "original_learner_mean_cost": rossman_result["learner"]["mean"],
                "interpretation": "A code-path sensitivity check. Its small change alone is not evidence of a material research finding.",
            },
        },
        "elapsed_seconds": time.perf_counter() - started,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "audit_results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out / "audit_results.json"),
                      "synthetic_cost_mean": synthetic_result["learner"]["mean"],
                      "rossmann_cost_mean": rossman_result["learner"]["mean"],
                      "DP_finding": dp_finding["status"],
                      "timing_replacements": timing_replacements,
                      "input_unchanged": all(v["unchanged"] for v in result["inputs"].values()),
                      "elapsed_seconds": result["elapsed_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
