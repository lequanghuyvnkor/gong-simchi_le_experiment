"""Algorithm 3, Section 7.1: full-feedback, backward episodic Q learning.

Exact tabular sweeps on the reachable integer MDP of fql_model; no learned
transition model, exploration bonus, base-stock restriction or demand oracle.
"""

from dataclasses import dataclass
from itertools import product

import numpy as np

from fql_model import HORIZON, FQLSpec, Pair, StockState, flow, validate_demand


def frozen(array):
    result = np.array(array, copy=True)
    result.setflags(write=False)
    return result


class StateGrid:
    def __init__(self, spec: FQLSpec, phase: int):
        if phase == 1:
            self.low = np.array(spec.initial_state.key)
            self.shape = (1, 1, 1, 1)
        else:
            self.low = np.array(tuple(s - (phase - 1) * spec.demand_cap for s in spec.initial_stock) + (0, 0))
            self.shape = tuple((phase - 1) * spec.demand_cap + (phase - 2) * q + 1 for q in spec.max_order) + tuple(q + 1 for q in spec.max_order)
        self.values = frozen(np.array(list(product(*(range(int(a), int(a + b)) for a, b in zip(self.low, self.shape)))), dtype=np.int64))

    def index(self, state: StockState) -> int:
        coords = np.array(state.key) - self.low
        if np.any(coords < 0) or np.any(coords >= self.shape):
            raise ValueError("Trạng thái không thuộc miền tới được của ngày này.")
        return int(np.ravel_multi_index(tuple(coords), self.shape))

    def state(self, index: int) -> StockState:
        row = self.values[index]
        return StockState(tuple(row[:2]), tuple(row[2:]))

    def next_indices(self, net: np.ndarray, actions: np.ndarray) -> np.ndarray:
        # Matrix (current state, joint action), matching row-major Q layout.
        shape = (len(net), len(actions))
        coords = [np.broadcast_to(net[:, i, None] - self.low[i], shape) for i in range(2)]
        coords += [np.broadcast_to(actions[None, :, i] - self.low[i + 2], shape) for i in range(2)]
        return np.ravel_multi_index(tuple(coords), self.shape)


@dataclass(frozen=True)
class FQLChoice:
    day: int
    phase: int
    state: StockState
    order: Pair
    q_values: tuple[float, ...]
    chosen_index: int
    tie_count: int


@dataclass(frozen=True)
class FQLObservation:
    choice: FQLChoice
    demand: Pair


@dataclass(frozen=True)
class StageUpdate:
    phase: int
    demand: Pair
    alpha: float
    q_before: np.ndarray
    reward: np.ndarray
    bootstrap: np.ndarray
    target: np.ndarray
    q_after: np.ndarray


@dataclass(frozen=True)
class FQLEpisode:
    episode: int
    observations: tuple[FQLObservation, ...]
    # The actual execution order is day 3, then day 2, then day 1.
    updates: tuple[StageUpdate, ...]

    def snapshot(self, count: int):
        if not 0 <= count <= HORIZON:
            raise ValueError("Bước phát lại phải từ 0 đến 3.")
        by_phase = {u.phase: u for u in self.updates}
        applied = {u.phase for u in self.updates[:count]}
        return tuple(by_phase[h].q_after if h in applied else by_phase[h].q_before for h in range(1, HORIZON + 1))


class FQL:
    def __init__(self, spec: FQLSpec):
        self.spec = spec
        self.actions = frozen(np.array(list(product(*(range(q + 1) for q in spec.max_order))), dtype=np.int64))
        self.grids = tuple(StateGrid(spec, h) for h in range(1, HORIZON + 1))
        self.q = [np.full((len(g.values), len(self.actions)), float(HORIZON)) for g in self.grids]
        self.state = spec.initial_state
        self.days_observed = 0
        self.pending: list[FQLObservation] = []
        self.traces: list[FQLEpisode] = []
        self._action_cost = self.actions @ np.array(spec.purchase) + np.any(self.actions > 0, axis=1) * spec.fixed_fee

    @property
    def entry_count(self):
        return sum(q.size for q in self.q)

    def plan(self) -> FQLChoice:
        phase = self.days_observed % HORIZON + 1
        row = self.q[phase - 1][self.grids[phase - 1].index(self.state)]
        best = int(np.argmax(row))  # actions are lexicographically increasing.
        return FQLChoice(
            self.days_observed + 1, phase, self.state, tuple(int(v) for v in self.actions[best]),
            tuple(float(v) for v in row), best, int(np.count_nonzero(row == row[best])),
        )

    def observe(self, demand: Pair) -> FQLEpisode | None:
        demand = validate_demand(self.spec, demand)
        choice = self.plan()
        result = flow(self.spec, self.state, choice.order, demand)
        self.pending.append(FQLObservation(choice, demand))
        self.days_observed += 1
        self.state = result.closing
        if choice.phase != HORIZON:
            return None
        trace = self._update()
        self.traces.append(trace)
        self.pending = []
        self.state = self.spec.initial_state
        return trace

    def _update(self) -> FQLEpisode:
        episode = len(self.traces) + 1
        alpha = (HORIZON + 1) / (HORIZON + episode)
        updates = []
        for offset in reversed(range(HORIZON)):
            demand = self.pending[offset].demand
            states = self.grids[offset].values
            net = states[:, :2] + states[:, 2:] - np.array(demand)
            stock_cost = np.maximum(net, 0) @ np.array(self.spec.holding)
            backlog_cost = np.maximum(-net, 0) @ np.array(self.spec.backlog_rate)
            cost = (stock_cost + backlog_cost)[:, None] + self._action_cost[None, :]
            reward = 1.0 - cost / self.spec.cost_bound
            if offset == HORIZON - 1:
                bootstrap = np.zeros_like(reward)
            else:
                indices = self.grids[offset + 1].next_indices(net, self.actions)
                # Deliberately uses the NEXT STAGE Q just updated in this sweep.
                bootstrap = self.q[offset + 1].max(axis=1)[indices]
            target = reward + bootstrap
            previous = self.q[offset]
            updated = (1 - alpha) * previous + alpha * target
            updates.append(StageUpdate(offset + 1, demand, alpha, frozen(previous), frozen(reward), frozen(bootstrap), frozen(target), frozen(updated)))
            self.q[offset] = updated
        return FQLEpisode(episode, tuple(self.pending), tuple(updates))
