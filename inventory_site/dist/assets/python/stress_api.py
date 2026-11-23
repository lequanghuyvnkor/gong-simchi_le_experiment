"""Bounded, interactive stress experiments over the existing teaching cores.

The demand source is temporarily injected at the environment boundary. Learners
still decide first and receive only their model's permitted feedback. The worker
serializes calls, and the original source is restored even after an exception.
Manual Lab sessions are separate objects and are never reset by this module.
"""
from contextlib import contextmanager
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import platform

import numpy as np

import experiment
import fql_experiment
import mimic_ql
from experiment import PairedRun
from lab_api import Lab, integer, scalar

SCENARIOS = {
    "native": ("Nhu cầu gốc", "within", "Phân phối theo pha của bản học; load=1 giữ bộ sinh gốc."),
    "zero": ("Không có nhu cầu", "within", "Đường cầu 0 để kiểm tra tồn dư và chi phí."),
    "steady": ("Nhu cầu đều", "within", "Phân phối cố định qua các pha, vẫn lặp theo H=3."),
    "peak": ("Đỉnh theo chu kỳ", "within", "Pha thứ hai có nhu cầu cao; phân phối lặp đúng H=3."),
    "alternating": ("Luân phiên hai ngày", "outside", "Chu kỳ 2 không trùng H=3; stress ngoài giả định."),
    "burst": ("Bùng cầu rồi lắng", "outside", "Burst đầu đường chạy, sau đó nhu cầu thấp; không dừng theo pha."),
    "drift": ("Đổi mức giữa chừng", "outside", "Phân phối đổi giữa chân trời; stress ngoài giả định lặp."),
}


def number(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} phải hữu hạn trong [{low}, {high}].")
    return float(value)


def config_from(raw):
    raw = raw or {}
    allowed = {"kind", "scenario", "seed", "seeds", "cycles", "load", "bounds", "confidence", "reference", "capacity", "holding", "penalty"}
    if set(raw) - allowed:
        raise ValueError("Cấu hình có trường chưa hỗ trợ: " + ", ".join(sorted(set(raw)-allowed)))
    c = {"kind":"meta", "scenario":"peak", "seed":9000, "seeds":3, "cycles":6,
         "load":1.0, "bounds":"practical", "confidence":1.0, "reference":"phase",
         "capacity":20, "holding":1.0, "penalty":4.0, **raw}
    if c["kind"] not in ("hql", "meta", "fql", "mimic") or c["scenario"] not in SCENARIOS:
        raise ValueError("Mô hình hoặc kịch bản chưa được hỗ trợ.")
    for name, lo, hi in (("seed",0,2147483643),("seeds",1,5),("cycles",1,20),("capacity",4,40)):
        integer(c[name], name)
        if not lo <= c[name] <= hi:
            raise ValueError(f"{name} phải trong [{lo}, {hi}].")
    for name, lo, hi in (("load",.25,2.0),("confidence",.25,4.0),("holding",.1,10.0),("penalty",.1,20.0)):
        c[name] = number(c[name], name, lo, hi)
    if c["bounds"] not in ("practical", "paper") or c["reference"] not in ("fixed", "phase"):
        raise ValueError("Cận hoặc baseline không hợp lệ.")
    if c["kind"] in ("fql", "mimic"):
        defaults = {"bounds":"practical","confidence":1.0,"capacity":20,"holding":1.0,"penalty":4.0}
        for key, default in defaults.items():
            if key in raw and raw[key] != default:
                raise ValueError(key + " chỉ áp dụng cho HQL/Meta-HQL trong bản này.")
            c.pop(key)
    return c


@contextmanager
def demand_source(kind, demand):
    module, name = (experiment, "sample_demand") if kind in ("hql", "meta") else (
        (mimic_ql if kind == "mimic" else fql_experiment), "sample_fql_demand")
    original = getattr(module, name)
    setattr(module, name, lambda config, day: demand)
    try:
        yield
    finally:
        setattr(module, name, original)


class StressSession:
    def __init__(self, options=None):
        self.config = config_from(options)
        self.rows, self.results, self.failures = [], [], []
        self.checks = {}
        self.lab = None
        self.last = None
        self.completed = 0
        self.metadata = {"variant":"inventory_hub_stress_v1", "python":platform.python_version(),
                         "numpy":np.__version__, "cost_scope":"during_learning_only",
                         "ci":"95% paired Student t across completed independent seeds; descriptive small sample",
                         "source_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                          for p in sorted(Path(__file__).parent.glob("*.py"))}}

    @property
    def total(self):
        return self.config["seeds"] * self.config["cycles"] * 3

    def _new_seed(self):
        c = self.config
        options = {"seed":c["seed"]+len(self.results),"cycles":c["cycles"]}
        options.update({key:c[key] for key in ("bounds","capacity","holding","penalty") if key in c})
        self.lab = Lab(c["kind"], options)
        if c["kind"] in ("hql", "meta"):
            practical = c["bounds"] == "practical"
            self.lab.run = PairedRun(self.lab.run.config, (.001 if practical else 8.)*c["confidence"],
                                     .001 if practical else 1.)

    def demand(self, day):
        c, cfg = self.config, self.lab.run.config
        kind, scenario, load = c["kind"], c["scenario"], c["load"]
        if scenario == "native" and load == 1:
            return (experiment.sample_demand(cfg, day) if kind in ("hql", "meta")
                    else fql_experiment.sample_fql_demand(cfg, day))
        full = kind in ("fql", "mimic")
        cap = cfg.spec.demand_cap if full else cfg.capacity
        if scenario == "zero":
            return (0, 0) if full else 0
        phase = (day-1) % 3
        level = {"steady":.4, "peak":(.15,.9,.3)[phase],
                 "alternating":.9 if day % 2 else .05,
                 "burst":.95 if day <= 3 else .1,
                 "drift":.2 if day <= cfg.total_days//2 else .85}.get(scenario, .4)
        rng = np.random.default_rng(np.random.SeedSequence([cfg.seed,day,719]))
        if scenario == "native":
            means = np.array(cfg.demand_means[phase]) * load
        else:
            means = np.array([level, level*.75])*cap*load if full else cap*level*load
        if full:
            # Changes in load saturate the declared support, never clip a draw.
            probability = np.minimum(np.array(means)/cap, 1.0)
            return tuple(int(v) for v in rng.binomial(cap, probability))
        return int(rng.poisson(means))

    def reference_action(self, day):
        c, run = self.config, self.lab.run
        fraction = (.3,.7,.4)[(day-1)%3] if c["reference"] == "phase" else .5
        if c["kind"] in ("hql", "meta"):
            return max(run.inventory, round(c["capacity"]*fraction))
        cap = run.config.spec.max_order
        return [round(cap[0]*fraction), round(cap[1]*(1-fraction) if c["reference"] == "phase" else cap[1]*fraction)]

    def check(self, name, condition, seed, day):
        item = self.checks.setdefault(name, {"passed":0,"total":0})
        item["total"] += 1
        if condition:
            item["passed"] += 1
        else:
            self.failures.append({"check":name,"seed":seed,"day":day})

    def step(self):
        if self.completed >= self.total:
            raise ValueError("Đã hoàn tất cấu hình stress này.")
        if self.lab is None or self.lab.snapshot()["finished"]:
            self._new_seed()
        lab, c = self.lab, self.config
        day = len(lab.run.human)+1
        seed = lab.run.config.seed
        demand = self.demand(day)
        with demand_source(c["kind"], demand):
            s = lab.step(self.reference_action(day))
        self.completed += 1
        a, h = s["algorithm"], s["human"]
        self.check("common_demand", a["demand"] == h["demand"], seed, day)
        self.check("finite_cost", math.isfinite(a["cost"]) and math.isfinite(h["cost"]), seed, day)
        if c["kind"] in ("hql", "meta"):
            for actor in (a,h):
                self.check("material_balance", actor["opening"]+actor["ordered"]-actor["sales"] == actor["remaining"], seed, day)
                self.check("lost_sales_balance", actor["sales"]+actor["lost"] == actor["demand"], seed, day)
            self.check("learner_inventory", lab.run.agent.inventory == a["next"], seed, day)
        else:
            for actor, record in ((a,lab.run.algorithm[-1]),(h,lab.run.human[-1])):
                f = record.flow
                self.check("material_balance", all(n+p-d==end for n,p,d,end in zip(f.opening.net,f.opening.pipeline,f.demand,f.closing.net)), seed, day)
                self.check("pipeline_and_cost", f.closing.pipeline == f.order and abs(sum(actor["cost_parts"].values())-actor["cost"])<1e-9, seed, day)
            if c["kind"] == "mimic":
                self.check("physical_never_resets", lab.run.algorithm[-1].next_state == lab.run.algorithm[-1].flow.closing, seed, day)
                self.check("virtual_clock", lab.run.virtual_learner.days_observed == day, seed, day)
        row = {"seed":seed,"day":day,"kind":c["kind"],"scenario":c["scenario"],
               "reference_cost":h["cost"],"learner_cost":a["cost"],
               "reference_total":s["sum_human"],"learner_total":s["sum_algorithm"],
               "demand":a["demand"],"order":a["ordered"],"stock":a["remaining"],
               "backlog":a.get("backlog",0),"lost":a.get("lost",0),"pipeline":a.get("pipeline",0),
               "virtual":s.get("virtual"),"virtual_reset":s.get("virtual_reset",False),
               "limited":s.get("limited",[False,False])}
        self.rows.append(row)
        self.last = {key:value for key,value in s.items() if key != "history"}
        if s["finished"]:
            self.results.append({"seed":seed,"reference_cost":s["sum_human"],"learner_cost":s["sum_algorithm"],
                                 "difference":s["sum_human"]-s["sum_algorithm"]})
        return self.snapshot()

    def snapshot(self):
        diffs = np.array([r["difference"] for r in self.results])
        n = len(diffs)
        interval = None
        if n >= 2:
            t = {1:12.7062047364,2:4.3026527297,3:3.1824463053,4:2.7764451052}[n-1]
            half = float(t*np.std(diffs,ddof=1)/math.sqrt(n))
            interval = [float(diffs.mean()-half),float(diffs.mean()+half)]
        scenario = SCENARIOS[self.config["scenario"]]
        return {"config":self.config,"completed":self.completed,"total":self.total,
                "finished":self.completed == self.total,"last":self.last,"rows":self.rows,
                "results":self.results,"checks":self.checks,"failures":self.failures,
                "scenario":{"label":scenario[0],"scope":scenario[1],"description":scenario[2]},
                "summary":{"seeds_completed":n,"mean_difference":float(diffs.mean()) if n else None,"ci95":interval}}

    def export(self):
        stream = io.StringIO()
        if self.rows:
            writer = csv.DictWriter(stream,fieldnames=list(self.rows[0]))
            writer.writeheader()
            for row in self.rows:
                writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list,tuple)) else v for k,v in row.items()})
        return {"report":{**self.snapshot(),"metadata":self.metadata},"csv":"\ufeff"+stream.getvalue()}


_STRESS = None


def handle_json(raw):
    global _STRESS
    request = json.loads(raw)
    op = request.get("op")
    if op == "stress_reset":
        session = StressSession(request.get("config"))
        _STRESS = session  # invalid config never replaces the current result
        result = session.snapshot()
    elif _STRESS is None:
        raise ValueError("Hãy áp dụng thiết kế stress trước.")
    elif op == "stress_step":
        result = _STRESS.step()
    elif op == "stress_snapshot":
        result = _STRESS.snapshot()
    elif op == "stress_export":
        result = _STRESS.export()
    else:
        raise ValueError("Thao tác stress không hợp lệ.")
    return json.dumps(result,default=scalar,ensure_ascii=False,allow_nan=False)
