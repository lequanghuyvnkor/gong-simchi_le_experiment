"""Small finite episodic, two-product backlogging MDP with one-day lead time.

The three-day episode is a teaching contract: record the terminal stock,
backlog and pipeline, give no terminal value, then start an independent episode.
No balance is clipped; every reachable integer state has a tabular Q entry.
"""

from dataclasses import dataclass, field
from math import isfinite
from numbers import Integral

import numpy as np


HORIZON = 3
Pair = tuple[int, int]


def integer_pair(name: str, values, low: int = 0) -> Pair:
    if len(values) != 2 or any(isinstance(v, bool) or not isinstance(v, Integral) or v < low for v in values):
        raise ValueError(f"{name} phải gồm hai số nguyên ≥ {low}.")
    return tuple(int(v) for v in values)


def rates(name: str, values) -> tuple[float, float]:
    if len(values) != 2 or any(not isfinite(v) or v < 0 for v in values):
        raise ValueError(f"{name} phải gồm hai mức phí hữu hạn, không âm.")
    return tuple(float(v) for v in values)


@dataclass(frozen=True)
class FQLSpec:
    """Known physics and costs. Contains no demand means, seed or future data."""

    max_order: Pair = (3, 3)
    initial_stock: Pair = (1, 1)
    demand_cap: int = 4
    purchase: tuple[float, float] = (1.0, 1.5)
    holding: tuple[float, float] = (0.5, 0.5)
    backlog_rate: tuple[float, float] = (4.0, 5.0)
    fixed_fee: float = 2.0

    def __post_init__(self):
        for name in ("max_order", "initial_stock"):
            object.__setattr__(self, name, integer_pair(name, getattr(self, name)))
        if any(v > 4 for v in self.max_order) or any(v > 5 for v in self.initial_stock):
            raise ValueError("Bản học dùng hạn mức đặt ≤ 4 và tồn ban đầu ≤ 5 mỗi sản phẩm.")
        if isinstance(self.demand_cap, bool) or not isinstance(self.demand_cap, Integral) or not 1 <= self.demand_cap <= 4:
            raise ValueError("Giới hạn nhu cầu phải là số nguyên từ 1 đến 4.")
        for name in ("purchase", "holding", "backlog_rate"):
            object.__setattr__(self, name, rates(name, getattr(self, name)))
        if not isfinite(self.fixed_fee) or self.fixed_fee < 0:
            raise ValueError("Phí đặt chung phải hữu hạn, không âm.")
        if self.cost_bound <= 0:
            raise ValueError("Cần ít nhất một mức phí dương để chuẩn hóa Q.")

    @property
    def initial_state(self):
        return StockState(self.initial_stock, (0, 0))

    @property
    def cost_bound(self) -> float:
        return self.bound_for_horizon(HORIZON)

    def bound_for_horizon(self, horizon: int) -> float:
        if isinstance(horizon, bool) or not isinstance(horizon, Integral) or horizon < 1:
            raise ValueError("Chân trời episode phải là số nguyên dương.")
        # Conservative daily bound over ALL reachable states and demand support.
        # On day h, net+arrival is bounded by initial-h*Dmax and
        # initial+(h-1)*qmax, uniformly over the requested horizon.
        bound = self.fixed_fee + sum(c * q for c, q in zip(self.purchase, self.max_order))
        for initial, q, hold, back in zip(self.initial_stock, self.max_order, self.holding, self.backlog_rate):
            bound += max(hold * (initial + (horizon - 1) * q), back * max(horizon * self.demand_cap - initial, 0))
        return float(bound)


@dataclass(frozen=True)
class FQLConfig:
    spec: FQLSpec = field(default_factory=FQLSpec)
    cycles: int = 6
    # Time-major: mean (A, B) for each of the three phases.
    demand_means: tuple[tuple[float, float], ...] = ((1.0, 2.0), (3.0, 1.0), (2.0, 3.0))
    seed: int = 42

    def __post_init__(self):
        if isinstance(self.cycles, bool) or not isinstance(self.cycles, Integral) or not 1 <= self.cycles <= 20:
            raise ValueError("Số chu kỳ phải từ 1 đến 20.")
        if isinstance(self.seed, bool) or not isinstance(self.seed, Integral) or self.seed < 0:
            raise ValueError("Seed phải là số nguyên không âm.")
        if len(self.demand_means) != HORIZON or any(
            len(p) != 2 or any(not isfinite(m) or not 0 <= m <= self.spec.demand_cap for m in p)
            for p in self.demand_means
        ):
            raise ValueError("Cần 3 cặp trung bình nhu cầu trong khoảng 0 đến giới hạn nhu cầu.")

    @property
    def total_days(self):
        return HORIZON * self.cycles


@dataclass(frozen=True)
class StockState:
    # Signed net inventory BEFORE today's scheduled arrival, plus that arrival.
    net: Pair
    pipeline: Pair

    def __post_init__(self):
        if len(self.net) != 2 or any(isinstance(v, bool) or not isinstance(v, Integral) for v in self.net):
            raise ValueError("Tồn ròng phải gồm hai số nguyên có dấu.")
        object.__setattr__(self, "net", tuple(int(v) for v in self.net))
        object.__setattr__(self, "pipeline", integer_pair("Hàng đang về", self.pipeline))

    @property
    def on_hand(self) -> Pair:
        return tuple(max(v, 0) for v in self.net)

    @property
    def backlog(self) -> Pair:
        return tuple(max(-v, 0) for v in self.net)

    @property
    def key(self):
        return self.net + self.pipeline


def validate_order(spec: FQLSpec, order) -> Pair:
    order = integer_pair("Đơn đặt", order)
    if any(q > cap for q, cap in zip(order, spec.max_order)):
        raise ValueError("Đơn đặt vượt hạn mức mỗi sản phẩm.")
    return order


def validate_demand(spec: FQLSpec, demand) -> Pair:
    demand = integer_pair("Nhu cầu", demand)
    if any(d > spec.demand_cap for d in demand):
        raise ValueError("Nhu cầu vượt miền hữu hạn đã công bố; không cắt ngọn nhu cầu.")
    return demand


@dataclass(frozen=True)
class Flow:
    opening: StockState
    order: Pair
    demand: Pair
    old_filled: Pair
    new_filled: Pair
    closing: StockState
    purchase_cost: float
    fixed_cost: float
    holding_cost: float
    backlog_cost: float

    @property
    def total_cost(self):
        return self.purchase_cost + self.fixed_cost + self.holding_cost + self.backlog_cost


def flow(spec: FQLSpec, state: StockState, order: Pair, demand: Pair) -> Flow:
    order = validate_order(spec, order)
    demand = validate_demand(spec, demand)
    supply = tuple(a + b for a, b in zip(state.on_hand, state.pipeline))
    old = tuple(min(a, b) for a, b in zip(supply, state.backlog))
    new = tuple(min(a - b, d) for a, b, d in zip(supply, old, demand))
    end = tuple(n + arrival - d for n, arrival, d in zip(state.net, state.pipeline, demand))
    closing = StockState(end, order)
    return Flow(
        state, order, demand, old, new, closing,
        sum(c * q for c, q in zip(spec.purchase, order)),
        spec.fixed_fee if any(order) else 0.0,
        sum(c * v for c, v in zip(spec.holding, closing.on_hand)),
        sum(c * v for c, v in zip(spec.backlog_rate, closing.backlog)),
    )


@dataclass(frozen=True)
class FQLDay:
    day: int
    flow: Flow
    next_state: StockState

    @property
    def phase(self):
        return (self.day - 1) % HORIZON + 1

    @property
    def cycle(self):
        return (self.day - 1) // HORIZON + 1

    @property
    def terminal(self):
        return self.phase == HORIZON


def simulate_fql_day(config: FQLConfig, day: int, state: StockState, order: Pair, demand: Pair) -> FQLDay:
    if isinstance(day, bool) or not isinstance(day, Integral) or not 1 <= day <= config.total_days:
        raise ValueError("Ngày nằm ngoài thí nghiệm.")
    result = flow(config.spec, state, order, demand)
    next_state = config.spec.initial_state if day % HORIZON == 0 else result.closing
    return FQLDay(day, result, next_state)


def sample_fql_demand(config: FQLConfig, day: int) -> Pair:
    if not 1 <= day <= config.total_days:
        raise ValueError("Ngày nằm ngoài thí nghiệm.")
    mean = np.asarray(config.demand_means[(day - 1) % HORIZON])
    rng = np.random.default_rng(np.random.SeedSequence([config.seed, day, 3001]))
    # A bounded distribution, not clipped Poisson. Support is known; p is not.
    return tuple(int(v) for v in rng.binomial(config.spec.demand_cap, mean / config.spec.demand_cap))
