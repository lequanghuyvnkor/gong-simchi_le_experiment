"""Reproduce a selected interactive stress config, or bounded software smoke checks.

This does not execute the 32-test research specification in experiments/stress_tests.
Python 3.10+ and NumPy are required; raw datasets are never read.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"inventory_site/dist/assets/python"))
from stress_api import SCENARIOS, StressSession


def run(config):
    session=StressSession(config)
    while session.completed<session.total:
        session.step()
    return session


def main():
    p=argparse.ArgumentParser(description=__doc__)
    choice=p.add_mutually_exclusive_group(required=True)
    choice.add_argument("--config",type=Path)
    choice.add_argument("--smoke",action="store_true")
    p.add_argument("--output-dir",type=Path,default=ROOT/"local_checks/interactive_stress")
    args=p.parse_args()
    out=args.output_dir.resolve()
    for private in (ROOT/"inputs",Path('/workspace/inputs')):
        if out==private or private in out.parents:p.error("Do not write to original inputs.")
    out.mkdir(parents=True,exist_ok=True)
    if args.smoke:
        records=[]
        for kind in ("hql","meta","fql","mimic"):
            for scenario in SCENARIOS:
                session=run({"kind":kind,"scenario":scenario,"cycles":3,"seeds":2})
                s=session.snapshot()
                records.append({"config":s["config"],"steps":s["completed"],"checks":s["checks"],"failures":s["failures"],"seed_results":s["results"]})
        report={"status":"passed" if all(not r["failures"] for r in records) else "failed",
                "scope":"Interactive teaching-model software smoke; not the research matrix or an efficacy benchmark",
                "created_utc":datetime.now(timezone.utc).isoformat(),"configurations":len(records),
                "total_steps":sum(r["steps"] for r in records),"research_matrix_executed":False,
                "metadata":session.metadata,"runs":records}
        (out/"smoke_results.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k not in ("metadata","runs")},ensure_ascii=False,indent=2))
        if report["status"]!="passed":raise SystemExit(1)
    else:
        raw=json.loads(args.config.read_text(encoding="utf-8"))
        config=raw.get("config",raw.get("report",{}).get("config",raw))
        session=run(config)
        data=session.export()
        (out/"report.json").write_text(json.dumps(data["report"],ensure_ascii=False,indent=2)+'\n')
        (out/"trace.csv").write_text(data["csv"],encoding="utf-8")
        print(json.dumps({"finished":True,"steps":session.completed,"failures":len(session.failures),"output_dir":str(out)},indent=2))
        if session.failures:raise SystemExit(1)


if __name__=="__main__":main()
