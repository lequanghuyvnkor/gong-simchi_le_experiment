"""Browser adapter using the project's Python simulation cores unchanged."""
import csv
import io
import json
from dataclasses import asdict

import numpy as np

from experiment import PairedRun
from model import Config
from fql_experiment import FQLRun
from fql_model import FQLConfig, FQLSpec
from hql import QUpdate

try:
    from mimic_ql import MimicRun
except ImportError:
    MimicRun = None


def scalar(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    raise TypeError(type(value).__name__)


def integer(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(label + " phải là số nguyên.")
    return value


class Lab:
    def __init__(self, kind="hql", options=None):
        options = options or {}
        if kind not in ("hql", "meta", "fql", "mimic"):
            raise ValueError("Mô hình không hợp lệ.")
        self.kind = kind
        self.bounds = options.get("bounds", "practical")
        if self.bounds not in ("practical", "paper"):
            raise ValueError("Chế độ cận không hợp lệ.")
        self.researcher = bool(options.get("researcher", True))
        seed = integer(options.get("seed", 42), "Seed")
        cycles = integer(options.get("cycles", 12 if kind == "meta" else 6), "Số chu kỳ")
        if not 1 <= cycles <= 20 or not 0 <= seed <= 2147483647:
            raise ValueError("Chu kỳ từ 1–20; seed từ 0–2147483647.")
        self.events = []
        if kind in ("hql", "meta"):
            capacity = integer(options.get("capacity", 20), "Sức chứa")
            if not 4 <= capacity <= 40:
                raise ValueError("Sức chứa bản học từ 4–40.")
            config = Config(capacity=capacity, initial_inventory=min(3, capacity),
                            holding_rate=float(options.get("holding", 1)),
                            penalty_rate=float(options.get("penalty", 4)), seed=seed,
                            cycles=cycles, discard_at_cycle_end=kind == "hql")
            practical = self.bounds == "practical"
            self.run = PairedRun(config, .001 if practical else 8., .001 if practical else 1.)
        else:
            config = FQLConfig(spec=FQLSpec(), seed=seed, cycles=cycles)
            if kind == "mimic":
                if MimicRun is None:
                    raise ValueError("Mimic-QL chưa có bản cài đặt đã đối chiếu nguồn.")
                self.run = MimicRun(config)
            else:
                self.run = FQLRun(config)

    def step(self, action):
        if self.kind in ("hql", "meta"):
            if isinstance(action, bool) or not isinstance(action, int):
                raise ValueError("Mức hàng phải là số nguyên.")
            self.run.step(action)
        else:
            if not isinstance(action, (list, tuple)) or len(action) != 2:
                raise ValueError("Cần số lượng đặt cho A và B.")
            self.run.step(tuple(action))
        return self.snapshot()

    def snapshot(self):
        run = self.run
        day = len(run.human)
        base = {"kind": self.kind, "day": day, "phase": day % 3 + 1,
                "total_days": run.config.total_days, "finished": day >= run.config.total_days,
                "seed": run.config.seed, "researcher": self.researcher, "bounds": self.bounds}
        if self.kind in ("hql", "meta"):
            last = run.human[-1] if day else None
            other = run.hql_history[-1] if day else None
            base.update(capacity=run.config.capacity, manual_opening=run.inventory,
                        observation="Doanh số riêng bị kiểm duyệt", label=run.agent.label,
                        history=run.comparison_rows(self.researcher),
                        alpha=None, q_updates=0,
                        human=self.lost_day(last), algorithm=self.lost_day(other),
                        status=run.choices[-1].status if day and self.kind == "meta" else "run",
                        arms=[asdict(a) for a in run.agent.states()] if self.kind == "meta" else [])
            traces = [step.q_trace for step in run.agent.steps if step.q_trace is not None] if self.kind == "meta" else run.agent.traces
            if traces:
                trace = traces[-1]
                base.update(alpha=trace.alpha, q_updates=sum(isinstance(e, QUpdate) for e in trace.events))
            base["sum_human"] = sum((r.total_cost if self.researcher else r.pseudo_cost) for r in run.human)
            base["sum_algorithm"] = sum((r.total_cost if self.researcher else r.pseudo_cost) for r in run.hql_history)
            base["cost_label"] = "Chi phí thực của mô phỏng" if self.researcher else "Chi phí thay thế quan sát được"
        else:
            human = run.human[-1] if day else None
            algorithm = run.algorithm[-1] if day else None
            base.update(manual_opening=list(run.human_state.on_hand), max_order=list(run.config.spec.max_order),
                        observation="Nhu cầu được quan sát đầy đủ", label="FQL · lưới nguyên hữu hạn" if self.kind == "fql" else run.agent.label,
                        history=run.comparison_rows(), human=self.full_day(human), algorithm=self.full_day(algorithm),
                        sum_human=sum(r.flow.total_cost for r in run.human),
                        sum_algorithm=sum(r.flow.total_cost for r in run.algorithm),
                        cost_label="Chi phí thực của mô phỏng", status="run", arms=[],
                        alpha=run.agent.traces[-1].updates[0].alpha if self.kind == "fql" and run.agent.traces else None,
                        q_updates=3 if self.kind == "fql" and run.agent.traces else 0)
            if self.kind == "mimic":
                base.update(run.explanation())
                if base["human"]:
                    base["human"]["terminal"] = base["algorithm"]["terminal"] = False
        base["cycles"] = run.config.cycles
        return base

    def lost_day(self, result):
        if result is None:
            return None
        row = {"day": result.day, "opening": result.opening, "target": result.order_up_to,
               "ordered": result.ordered, "sales": result.sales, "remaining": result.remaining,
               "next": result.next_opening, "discarded": result.discarded, "pipeline": 0,
               "cost": result.total_cost if self.researcher else result.pseudo_cost,
               "demand": result.demand if self.researcher else None,
               "lost": result.lost if self.researcher else None}
        return row

    @staticmethod
    def full_day(result):
        if result is None:
            return None
        f = result.flow
        return {"day": result.day, "opening": list(f.opening.on_hand), "arrived": list(f.opening.pipeline),
                "ordered": list(f.order), "demand": list(f.demand), "old_filled": list(f.old_filled),
                "sales": list(f.new_filled), "remaining": list(f.closing.on_hand),
                "backlog": list(f.closing.backlog), "pipeline": list(f.closing.pipeline),
                "cost": f.total_cost, "cost_parts": {"Mua hàng": f.purchase_cost, "Phí đặt chung": f.fixed_cost,
                    "Lưu kho": f.holding_cost, "Nợ đơn": f.backlog_cost},
                "terminal": result.terminal}

    def q_detail(self, phase=1, action=0):
        horizon = self.run.artificial_horizon if self.kind == "mimic" else 3
        if not 1 <= phase <= horizon or action < 0:
            raise ValueError("Pha hoặc chỉ số lệnh ngoài miền hợp lệ.")
        if self.kind in ("hql", "meta"):
            if self.kind == "meta":
                completed = [s for s in self.run.agent.steps if s.q_trace is not None]
                if not completed:
                    return {"message": "Chưa có episode hoạt động hoàn tất."}
                learner = self.run.agent.learners[completed[-1].choice.arm - 1]
            else:
                learner = self.run.agent
            if not learner.traces:
                return {"message": "Bộ học đang thu thập đủ episode trước khi cập nhật Q."}
            trace = learner.traces[-1]
            event = next((e for e in trace.events if isinstance(e, QUpdate) and e.phase == phase and e.action == action), None)
            if event is None:
                return {"message": "Ứng viên này không được cập nhật trong episode vừa chọn.",
                        "available_actions": [e.action for e in trace.events if isinstance(e, QUpdate) and e.phase == phase]}
            return {"phase": phase, "action": action, "old_q": event.old_q, "alpha": event.alpha,
                    "reward": event.reward_sum, "bootstrap": event.bootstrap, "target": event.target,
                    "new_q": event.new_q, "tau": event.stopping_phase,
                    "trajectory": [asdict(s) for s in event.trajectory]}
        agent = self.run.agent
        if self.kind == "mimic":
            agent = self.run.virtual_learner
        if not agent.traces:
            return {"message": "Chưa có episode học hoàn tất để phát lại Q."}
        trace = agent.traces[-1]
        update = next(x for x in trace.updates if x.phase == phase)
        observation = trace.observations[phase - 1]
        index = agent.grids[phase - 1].index(observation.choice.state)
        a = min(max(int(action), 0), len(agent.actions)-1)
        return {"phase": phase, "action": list(agent.actions[a]), "old_q": float(update.q_before[index, a]),
                "alpha": update.alpha, "reward": float(update.reward[index, a]),
                "bootstrap": float(update.bootstrap[index, a]), "target": float(update.target[index, a]),
                "new_q": float(update.q_after[index, a]), "state": list(observation.choice.state.key),
                "trajectory": [], "tau": None}


_LAB = None
_LABS = {}


def handle_json(raw):
    global _LAB
    data = json.loads(raw)
    op = data.get("op")
    if op in ("reset", "select"):
        kind = data.get("kind", "hql")
        instance = _LABS.get(kind) if op == "select" else None
        if instance is None:
            instance = Lab(kind, data.get("options"))
        _LABS[kind] = instance
        _LAB = instance
        result = instance.snapshot()
    elif _LAB is None:
        raise ValueError("Hãy bắt đầu một lượt mô phỏng.")
    elif op == "step":
        result = _LAB.step(data.get("action"))
    elif op == "snapshot":
        result = _LAB.snapshot()
    elif op == "q":
        result = _LAB.q_detail(integer(data.get("phase", 1), "Pha"), integer(data.get("action", 0), "Chỉ số lệnh"))
    elif op == "export":
        rows = _LAB.snapshot()["history"]
        stream = io.StringIO()
        if rows:
            fields = list(dict.fromkeys(key for row in rows for key in row))
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        result = {"csv": "\ufeff" + stream.getvalue()}
    else:
        raise ValueError("Thao tác không hợp lệ.")
    return json.dumps(result, default=scalar, ensure_ascii=False, allow_nan=False)
