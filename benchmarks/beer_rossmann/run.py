"""Portable runner for the archived adapted benchmark (Python 3.10+)."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SAVED = REPO / "results/beer_rossmann"


def load_metrics(path):
    import numpy as np
    import pandas as pd
    with np.load(path, allow_pickle=False) as data:
        return pd.DataFrame({key: data[key] for key in data.files})


def initialize(root, snapshot=False):
    target = root / "outputs/condition_study"
    target.mkdir(parents=True, exist_ok=True)
    for source in (HERE / "config").glob("*.json"):
        dest = target / source.name
        if dest.exists() and dest.read_bytes() != source.read_bytes():
            raise ValueError(f"Refusing to replace a changed configuration: {dest}")
        if not dest.exists():
            shutil.copy2(source, dest)
    if snapshot:
        for source in SAVED.glob("*.npz"):
            load_metrics(source).to_csv(target / (source.stem + ".csv"), index=False)
        for source in SAVED.glob("*.json"):
            if source.name.startswith(("source_audit_", "diagnostics_")):
                shutil.copy2(source, target / source.name)
    return target


def verify(target):
    import numpy as np
    import pandas as pd
    checked = []
    for source in SAVED.glob("*.csv"):
        actual = pd.read_csv(target / source.name)
        expected = pd.read_csv(source)
        pd.testing.assert_frame_equal(actual, expected, check_dtype=False, rtol=1e-9, atol=1e-9)
        checked.append(source.name)
    actual = json.loads((target / "analysis_summary.json").read_text())
    expected = json.loads((SAVED / "analysis_summary.json").read_text())
    assert actual["primary_counts"] == expected["primary_counts"] == {"Meta-HQL-P": 18}
    assert actual["online_counts"] == expected["online_counts"] == {"SRDQN-A": 18}
    for algorithm, values in expected["core_means"].items():
        for metric, value in values.items():
            result = actual["core_means"][algorithm][metric]
            assert (result is None and value is None) or np.isclose(result, value, rtol=1e-9, atol=1e-9)
    return checked


def smoke(study):
    import numpy as np
    records = study.records([study.scenarios()[0]], [0], [1000, 1001])
    demand = study.demands(records, 700, 2001)
    evaluation = study.demands(records, 140, 2002)
    assert np.array_equal(demand, study.demands(records, 700, 2001))
    assert not np.array_equal(demand[0], demand[1])
    assert np.array_equal(demand[:, :350], study.demands(records, 350, 2001))
    penalty = np.ones(2)
    diagnostics = {}
    for kind in ["SRDQN-A", "Meta-HQL-P", "Meta-HQL-T"]:
        config = (json.loads((HERE / "config" / f"selected_{kind}.json").read_text())["config"]
                  if kind != "Meta-HQL-T" else {"action_scale": 1., "bandit_scale": 1.})
        result, diag = study.train(demand, evaluation, penalty, kind, config,
                                   study.identity(records), [700], log=False)
        assert all(np.isfinite(v).all() for v in result[700].values())
        assert diag.get("feedback_violations", 0) == 0
        diagnostics[kind] = diag
    for y in study.GRID:
        for d in [0., .3, 1.7, 6.2]:
            sales = min(y, d)
            for p in [1, 5, 10]:
                assert abs((y-sales+p*(d-sales))-(y-sales-p*sales)-p*d) < 1e-9
            for z in study.GRID[study.GRID <= y]:
                assert abs(min(z, d)-min(z, sales)) < 1e-9
    return diagnostics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["snapshot", "analyze", "smoke", "prepare-data", "core", "long", "source-beer", "source-ross", "gate-selected", "tune-dqn", "tune-meta"])
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--block", type=int, choices=range(6), default=0)
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error("Python 3.10+ required")
    root = args.run_dir.resolve()
    if root == REPO or (root.is_relative_to(REPO) and not root.is_relative_to(REPO / "local_checks")):
        parser.error("Use a run directory outside the repo or under local_checks/")
    if root.is_relative_to(Path('/workspace/inputs')) or "inputs" in root.parts:
        parser.error("Do not write into original inputs")
    os.environ["GONG_RUN_DIR"] = str(root)
    target = initialize(root, snapshot=args.stage == "snapshot")
    sys.path.insert(0, str(HERE))
    study = importlib.import_module("condition_study")
    if args.stage in ("snapshot", "analyze"):
        importlib.import_module("analyze_conditions").main()
        report = {"scope": "Reanalysis of archived policy metrics; no full retraining" if args.stage == "snapshot" else "Analysis of run-directory training outputs",
                  "tables_checked": verify(target) if args.stage == "snapshot" else []}
    elif args.stage == "smoke":
        report = {"scope": "700-period smoke run only, not the 18-condition result", "diagnostics": smoke(study)}
    else:
        actions = {"prepare-data": lambda: importlib.import_module("research_run").prepare(),
                   "core": lambda: study.run_core(args.block), "long": lambda: study.run_long(args.block),
                   "source-beer": lambda: study.sources("Beer"), "source-ross": lambda: study.sources("Rossmann"),
                   "gate-selected": lambda: study.gate(True), "tune-dqn": lambda: study.tune("SRDQN-A"),
                   "tune-meta": lambda: study.tune("Meta-HQL-P")}
        actions[args.stage]()
        report = {"scope": args.stage, "block": args.block}
    import numpy as np
    import pandas as pd
    report.update(python=sys.version, numpy=np.__version__, pandas=pd.__version__)
    (root / f"check_{args.stage}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
