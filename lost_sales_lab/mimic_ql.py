"""Declared teaching adaptation of the author's inventory-position mimic idea.

Primary source: Gong's MIT thesis (2023), pp.62-65,170-171. The virtual FQL
episode has length J=6, a multiple of true demand cycle H=3. Virtual time never
pauses. Physical stock, debt and pipeline never reset. The matching request
includes the virtual current order, then is limited by the physical per-SKU
actuator. This resolves a source notation ambiguity and is NOT a literal
replication of Algorithm 4 or an implementation with its regret guarantee.
"""
from dataclasses import dataclass, replace

from fql import FQL
from fql_model import (FQLConfig, Flow, FQLSpec, StockState, flow,
                       sample_fql_demand, validate_order)


def position(state):
    return tuple(n + p for n, p in zip(state.net, state.pipeline))


@dataclass(frozen=True)
class MatchChoice:
    day: int
    virtual_state: StockState
    physical_state: StockState
    virtual_order: tuple[int, int]
    requested: tuple[int, int]
    executed: tuple[int, int]
    limited: tuple[bool, bool]


@dataclass(frozen=True)
class ContinuousDay:
    day: int
    flow: Flow
    next_state: StockState
    terminal: bool = False


class MimicRun:
    def __init__(self, config: FQLConfig, artificial_horizon=6):
        if artificial_horizon not in (6, 9):
            raise ValueError("Bản học dùng J=6 hoặc 9, đều là bội của H=3.")
        spec = FQLSpec(max_order=(2, 2), initial_stock=(0, 0), demand_cap=2,
                       purchase=config.spec.purchase, holding=config.spec.holding,
                       backlog_rate=config.spec.backlog_rate, fixed_fee=config.spec.fixed_fee)
        self.config = replace(config, spec=spec, demand_means=((.5, 1.5), (1.5, .5), (1., 1.)))
        self.artificial_horizon = artificial_horizon
        self.virtual_learner = FQL(spec, horizon=artificial_horizon)
        self.agent = self
        self.label = "Mimic-QL · bản học ghép vị thế tồn, có hạn mức lệnh"
        self.human = []
        self.algorithm = []
        self.virtual = []
        self.choices = []

    @property
    def human_state(self):
        return self.human[-1].next_state if self.human else self.config.spec.initial_state

    @property
    def physical_state(self):
        return self.algorithm[-1].next_state if self.algorithm else self.config.spec.initial_state

    def plan(self):
        choice = self.virtual_learner.plan()
        real = self.physical_state
        ip_real, ip_virtual = position(real), position(choice.state)
        request = tuple(max(v + q - r, 0) for v, q, r in zip(ip_virtual, choice.order, ip_real))
        executed = tuple(min(q, cap) for q, cap in zip(request, self.config.spec.max_order))
        return MatchChoice(len(self.human) + 1, choice.state, real, choice.order, request,
                           executed, tuple(a != b for a, b in zip(request, executed)))

    def step(self, order):
        order = validate_order(self.config.spec, order)
        day = len(self.human) + 1
        if day > self.config.total_days:
            raise ValueError("Đã chạy đủ số ngày.")
        choice = self.plan()
        demand = sample_fql_demand(self.config, day)
        h = flow(self.config.spec, self.human_state, order, demand)
        a = flow(self.config.spec, self.physical_state, choice.executed, demand)
        v = flow(self.config.spec, choice.virtual_state, choice.virtual_order, demand)
        self.virtual_learner.observe(demand)
        self.human.append(ContinuousDay(day, h, h.closing))
        self.algorithm.append(ContinuousDay(day, a, a.closing))
        self.virtual.append(v)
        self.choices.append(choice)
        if day % self.artificial_horizon:
            assert self.virtual_learner.state == v.closing
        else:
            assert self.virtual_learner.state == self.config.spec.initial_state
        return self.human[-1]

    def comparison_rows(self):
        rows = []
        totals = [0., 0.]
        for human, algorithm, virtual, choice in zip(self.human, self.algorithm, self.virtual, self.choices):
            totals[0] += human.flow.total_cost
            totals[1] += algorithm.flow.total_cost
            row = {"Ngày": human.day, "Nhu cầu A": human.flow.demand[0], "Nhu cầu B": human.flow.demand[1],
                   "Bạn · lũy kế": totals[0], "Mimic-QL · lũy kế": totals[1],
                   "Bạn · chi phí ngày": human.flow.total_cost, "Mimic-QL · chi phí ngày": algorithm.flow.total_cost,
                   "H": 3, "J": self.artificial_horizon, "L": 1, "Seed": self.config.seed,
                   "Phương pháp": self.label, "Quy tắc giới hạn": "q=min(cap,max(IPảo+qảo−IPthực,0))",
                   "Reset hệ ảo": human.day % self.artificial_horizon == 0,
                   "Phạm vi": "Bản học điều chỉnh; chưa xác minh bảo đảm lý thuyết"}
            for i, product in enumerate(("A", "B")):
                for name, item in (("Bạn", human.flow), ("Mimic-QL", algorithm.flow), ("Ảo", virtual)):
                    row[f"{name} · tồn cuối {product}"] = item.closing.on_hand[i]
                    row[f"{name} · nợ cuối {product}"] = item.closing.backlog[i]
                    row[f"{name} · đang về {product}"] = item.closing.pipeline[i]
                row[f"Yêu cầu bù {product}"] = choice.requested[i]
                row[f"Lệnh thực {product}"] = choice.executed[i]
                row[f"Chạm hạn mức {product}"] = choice.limited[i]
            rows.append(row)
        return rows

    def explanation(self):
        day = len(self.human)
        virtual = self.virtual_learner.state
        actual = self.physical_state
        previous = self.choices[-1] if day else None
        return {"virtual": {"net": list(virtual.net), "stock": list(virtual.on_hand),
                            "backlog": list(virtual.backlog), "pipeline": list(virtual.pipeline)},
                "real_position": list(position(actual)), "virtual_position": list(position(virtual)),
                "synchronized": actual == virtual,
                "requested": list(previous.requested) if previous else [0, 0],
                "limited": list(previous.limited) if previous else [False, False],
                "virtual_reset": bool(day and day % self.artificial_horizon == 0),
                "artificial_horizon": self.artificial_horizon,
                "virtual_phase": day % self.artificial_horizon + 1,
                "status": "synced" if actual == virtual else "matching",
                "q_updates": self.artificial_horizon if self.virtual_learner.traces else 0,
                "alpha": self.virtual_learner.traces[-1].updates[0].alpha if self.virtual_learner.traces else None}
