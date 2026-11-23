import json
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"dist/assets/python"))
import experiment
import lab_api
import stress_api
from stress_api import StressSession


@pytest.mark.parametrize("kind",["hql","meta","fql","mimic"])
@pytest.mark.parametrize("scenario",list(stress_api.SCENARIOS))
def test_every_scenario_preserves_physics_and_finishes_paired_seeds(kind,scenario):
    a=StressSession({"kind":kind,"scenario":scenario,"seeds":2,"cycles":2,"load":1.5})
    while a.completed<a.total:a.step()
    s=a.snapshot()
    assert s["finished"] and not s["failures"]
    assert all(v["passed"]==v["total"] for v in s["checks"].values())
    assert len(s["rows"])==12 and len(s["results"])==2
    assert s["summary"]["ci95"][0] <= s["summary"]["mean_difference"] <= s["summary"]["ci95"][1]
    json.dumps(a.export(),allow_nan=False)


@pytest.mark.parametrize("kind",["hql","meta","fql","mimic"])
def test_native_demand_matches_original_model_and_stress_does_not_reset_manual_session(kind):
    baseline=lab_api.Lab(kind,{"seed":9000,"cycles":2})
    session=StressSession({"kind":kind,"scenario":"native","seeds":1,"cycles":2})
    lab_api.handle_json('{"op":"reset","kind":"hql"}')
    lab_api.handle_json('{"op":"step","action":10}')
    before=lab_api.handle_json('{"op":"snapshot"}')
    for day in range(1,7):
        session.step()
        baseline.step(max(baseline.snapshot()["manual_opening"],10) if kind in ("hql","meta") else [2,2])
        assert session.rows[-1]["demand"]==baseline.snapshot()["algorithm"]["demand"]
    assert lab_api.handle_json('{"op":"snapshot"}')==before


def test_replay_is_deterministic_and_reports_partial_results_without_invented_ci():
    c={"kind":"mimic","scenario":"drift","cycles":3,"seeds":3}
    a,b=StressSession(c),StressSession(c)
    assert a.snapshot()["summary"]["ci95"] is None
    for _ in range(27):a.step();b.step()
    assert a.snapshot()==b.snapshot()
    d=np.array([r["difference"] for r in a.results])
    half=4.3026527297*d.std(ddof=1)/np.sqrt(3)
    np.testing.assert_allclose(a.snapshot()["summary"]["ci95"],[d.mean()-half,d.mean()+half])
    count=a.completed
    with pytest.raises(ValueError):a.step()
    assert a.completed==count


@pytest.mark.parametrize("bad",[{"cycles":1.2},{"seeds":6},{"load":float("nan")},{"seed":True},{"kind":"mimic","capacity":40},{"__code__":"print(1)"}])
def test_invalid_configuration_does_not_replace_the_existing_result(bad):
    stress_api.handle_json('{"op":"stress_reset","config":{"cycles":1,"seeds":1}}')
    stress_api.handle_json('{"op":"stress_step"}')
    before=stress_api.handle_json('{"op":"stress_snapshot"}')
    with pytest.raises(ValueError):stress_api.handle_json(json.dumps({"op":"stress_reset","config":bad}))
    assert stress_api.handle_json('{"op":"stress_snapshot"}')==before


def test_environment_source_is_restored_even_if_a_run_raises(monkeypatch):
    original=experiment.sample_demand
    with pytest.raises(RuntimeError):
        with stress_api.demand_source("hql",0):
            assert experiment.sample_demand(None,1)==0
            raise RuntimeError("fixture")
    assert experiment.sample_demand is original
