"""Verify all 15 native chart datasets against repository results, plus provenance.

This checks the repository distribution; it does not rerun the original paper
or certify its theorems. Paper-only settings and illustrative numbers are
classified separately in evidence_map.md.
"""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
from docx import Document
from pptx import Presentation

HERE = Path(__file__).resolve().parent
REPO = HERE.parent


def csv(name):
    return pd.read_csv(REPO / "results/five_experiments" / (name + ".csv"))


def check(directory):
    manifest = json.loads((directory / "release_manifest.json").read_text())
    for name, record in manifest["outputs"].items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == record["sha256"], name
    prs = Presentation(directory / "Gong_Simchi_2024_Academic_60min_v4_repo.pptx")
    audit = json.loads((REPO / "results/replication_audit/audit_results.json").read_text())
    ross = audit["runs"]["rossmann"]
    synthetic = audit["runs"]["synthetic"]
    means = json.loads((REPO / "results/beer_rossmann/analysis_summary.json").read_text())["core_means"]
    cfo = json.loads((REPO / "results/cfo/summary.json").read_text())
    assumptions = json.loads((REPO / "reports/cfo/assumptions.json").read_text())
    expected = {
        10: [[ross[k]["mean"] for k in ["learner", "expert_advice", "near_OPT_vector", "best_iid"]]],
        11: [[ross[k]["mean"] for k in ["learner", "expert_advice"]]],
        12: [[synthetic["author_DP_policy_realized_cost"]["mean"], synthetic["candidate_feasible_policy"]["mean"]]],
        20: [[means[a][k] for k in ["online_cost", "frozen_cost"]] for a in ["SRDQN-A", "Meta-HQL-P"]],
        21: [[means[a]["frozen_cost"] for a in ["SRDQN-A", "Prior weekday", "Meta-HQL-P"]]],
        22: [[100*cfo["annual_p10_saving_per_sku_vs_weekday"]/1e6, assumptions["meta_incremental_setup_vnd_vs_existing_baseline"]/1e6, assumptions["meta_incremental_annual_running_vnd_vs_existing_baseline"]/1e6]],
        24: [csv("tn4_entropic_policies")[k].to_numpy() for k in ["mean_total", "cvar95"]],
        26: [csv("tn5_capital_policy_metrics").query("fixed_cost==@k").sort_values("annual_rate").mean_inventory.to_numpy() for k in [0, 8]],
        35: [[ross["learner"]["mean"], audit["runs"]["rossmann_episode_start_sensitivity"]["learner"]["mean"]]],
    }
    curves = csv("tn1_learning_curves")
    independent = csv("tn1_independent_runs")
    trace = csv("tn2_trace_seed0").set_index("day")
    volatility = csv("tn3_online_runs").query("penalty==4").groupby("volatility")[["avg_cost", "gap_vs_oracle"]].mean()
    gaps = csv("tn5_action_value_gaps")
    checked = []
    points = 0
    for number, slide in enumerate(prs.slides, 1):
        for shape in slide.shapes:
            if not shape.has_chart:
                continue
            chart = shape.chart
            categories = [x.label for x in chart.plots[0].categories]
            if number == 14:
                expected[number] = [curves[curves.policy==a].set_index("day").loc[[int(x)*7 for x in categories], "mean_daily_cost"].to_numpy() for a in ["Meta-HQL practical", "Oracle cyclic DP", "Best constant"]]
            elif number == 15:
                expected[number] = [independent[independent.policy==a].groupby("amplitude").avg_cost.mean().to_numpy() for a in ["Meta-HQL practical", "Oracle cyclic DP", "Best constant"]]
            elif number == 16:
                # Last point is the final day, labeled by floor(day / H).
                days = [int(x)*7 for x in categories[:-1]] + [int(trace.index.max())]
                expected[number] = [trace.loc[days, k].to_numpy() for k in ["candidate_count", "remaining_arms"]]
            elif number == 17:
                expected[number] = [trace.loc[[int(x) for x in categories], k].to_numpy() for k in ["x", "y"]]
            elif number == 18:
                expected[number] = [volatility[k].to_numpy() for k in ["avg_cost", "gap_vs_oracle"]]
            elif number == 27:
                expected[number] = [gaps[np.isclose(gaps.annual_rate, r)].set_index("inventory").loc[[int(x) for x in categories], "delta"].to_numpy() for r in [0, .3]] + [np.zeros(len(categories))]
            assert len(chart.series) == len(expected[number]), number
            for series, values in zip(chart.series, expected[number]):
                np.testing.assert_allclose(series.values, values, rtol=0, atol=5.1e-7, err_msg=f"slide {number}")
                points += len(values)
            checked.append(number)
    assert len(checked) == 15 and len(prs.slides) == 38
    question_table = " ".join(cell.text for shape in prs.slides[1].shapes if shape.has_table
                              for row in shape.table.rows for cell in row.cells)
    assert "Check benchmark and implementation fit" in question_table
    assert "Study confidence-bound sensitivity" in question_table
    with ZipFile(directory / "Gong_Simchi_2024_Academic_60min_v4_repo.pptx") as z:
        assert not [n for n in z.namelist() if n.startswith("ppt/media/")]
    doc = Document(directory / "Gong_Simchi_2024_Script_Tieng_Viet_60_phut_repo.docx")
    headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading") and p.text.startswith("Slide ")]
    assert len(headings) == 31, len(headings)
    assert "độ nhạy" in " ".join(p.text for p in doc.paragraphs).lower()
    return {"scope": "15 native chart datasets compared to saved project results; paper settings require cited original sources",
            "chart_slides": checked, "numeric_chart_points": points, "slide_count": 38,
            "script_main_slide_sections": 31, "third_party_image_blobs_in_release": 0}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory", type=Path, default=HERE)
    args = p.parse_args()
    result = check(args.directory)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
