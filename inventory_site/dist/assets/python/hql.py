"""Elimination-based HQL, Algorithm 1, Gong & Simchi-Levi (2024), §4.

Teaching discretization: integer order-up-to levels 0..M rather than the paper's
T-dependent fine grid. The learner receives ONLY its own censored sales.
"""

from dataclasses import dataclass
from math import isfinite, log, sqrt

import numpy as np

from model import CYCLE_LENGTH, _integer


@dataclass(frozen=True)
class Choice:
    day: int
    episode: int
    phase: int
    opening: int
    order_up_to: int
    ordered: int
    running: tuple[int, ...]
    best_q_action: int


@dataclass(frozen=True)
class Observation:
    choice: Choice
    sales: int


@dataclass(frozen=True)
class CounterfactualStep:
    phase: int
    stock: int
    observed_sales: int
    simulated_sales: int
    remaining: int
    reward: float


@dataclass(frozen=True)
class QUpdate:
    phase: int
    action: int
    old_q: float
    alpha: float
    reward_sum: float
    stopping_phase: int
    bootstrap: float
    target: float
    new_q: float
    trajectory: tuple[CounterfactualStep, ...]


@dataclass(frozen=True)
class Elimination:
    phase: int
    best_action: int
    best_q: float
    bound: float
    kept: tuple[int, ...]
    removed: tuple[int, ...]


@dataclass(frozen=True)
class ShiftTrim:
    phase: int
    cap: int
    kept: tuple[int, ...]
    removed: tuple[int, ...]
    restored: bool = False


@dataclass(frozen=True)
class EpisodeTrace:
    episode: int
    alpha: float
    bound: float
    q_before: tuple[tuple[float, ...], ...]
    q_after: tuple[tuple[float, ...], ...]
    active_before: tuple[tuple[bool, ...], ...]
    active_after: tuple[tuple[bool, ...], ...]
    observations: tuple[Observation, ...]
    events: tuple[QUpdate | Elimination | ShiftTrim, ...]

    def snapshot(self, count: int) -> tuple[np.ndarray, np.ndarray]:
        """Read-only replay of the first count events; never re-train the agent."""
        _integer("Bước xem lại", count)
        if count > len(self.events):
            raise ValueError("Bước xem lại vượt quá số cập nhật của chu kỳ.")
        q = np.array(self.q_before, dtype=float)
        active = np.array(self.active_before, dtype=bool)
        for event in self.events[:count]:
            if isinstance(event, QUpdate):
                q[event.phase - 1, event.action] = event.new_q
            else:
                active[event.phase - 1] = False
                active[event.phase - 1, list(event.kept)] = True
        return q, active


class HQL:
    def __init__(self, capacity: int, holding_rate: float, penalty_rate: float,
                 total_days: int, initial_inventory: int = 0, confidence_scale: float = 8.0):
        _integer("M", capacity, 1)
        _integer("T", total_days, 1)
        _integer("Tồn kho ban đầu", initial_inventory)
        if initial_inventory > capacity or total_days % CYCLE_LENGTH:
            raise ValueError("Tồn ban đầu phải ≤ M và số ngày phải là bội của 3.")
        if any(not isfinite(v) or v <= 0 for v in (holding_rate, penalty_rate, confidence_scale)):
            raise ValueError("Phí và hệ số cận tin cậy phải là số dương hữu hạn.")
        self.capacity = capacity
        self.holding_rate = float(holding_rate)
        self.penalty_rate = float(penalty_rate)
        self.total_days = total_days
        self.confidence_scale = float(confidence_scale)
        self.inventory = initial_inventory
        self.days_observed = 0
        self.q = np.full((CYCLE_LENGTH, capacity + 1), float(CYCLE_LENGTH))
        self.active = np.ones_like(self.q, dtype=bool)
        self.buffer: list[Observation] = []
        self.traces: list[EpisodeTrace] = []

    @property
    def label(self) -> str:
        return "HQL · cận bài báo" if self.confidence_scale == 8.0 else f"HQL minh họa · c={self.confidence_scale:g}"

    def plan(self) -> Choice:
        if self.days_observed >= self.total_days:
            raise ValueError("HQL đã chạy đủ số ngày của thí nghiệm.")
        phase = self.days_observed % CYCLE_LENGTH
        running = tuple(int(y) for y in np.flatnonzero(self.active[phase]))
        largest = max(running)
        target = max(self.inventory, largest)
        best = max(running, key=lambda y: self.q[phase, y])
        return Choice(
            day=self.days_observed + 1, episode=self.days_observed // CYCLE_LENGTH + 1,
            phase=phase + 1, opening=self.inventory, order_up_to=target,
            ordered=target - self.inventory, running=running, best_q_action=best,
        )

    def observe(self, sales: int) -> EpisodeTrace | None:
        """No true demand, true shortage cost, or human feedback enters here."""
        choice = self.plan()
        _integer("Lượng bán của HQL", sales)
        if sales > choice.order_up_to:
            raise ValueError("Lượng bán không thể vượt hàng sẵn bán của HQL.")
        self.buffer.append(Observation(choice, sales))
        self.days_observed += 1
        self.inventory = choice.order_up_to - sales
        if choice.phase != CYCLE_LENGTH:
            return None
        self.inventory = 0  # HQL here is the episodic lost-sales algorithm.
        trace = self._update_episode(choice.episode)
        self.traces.append(trace)
        self.buffer = []
        return trace

    def _update_episode(self, episode: int) -> EpisodeTrace:
        horizon = CYCLE_LENGTH
        alpha = (horizon + 1) / (horizon + episode)
        iota = 9 * log((self.capacity + 1) * self.total_days)
        # The paper uses k-1. At k=1 the confidence bound is uninformative:
        # retain all actions, rather than divide by zero or invent confidence.
        bound = float("inf") if episode == 1 else self.confidence_scale * sqrt(horizon**5 * iota / (episode - 1))
        old_active = self.active.copy()
        q_before = tuple(tuple(float(v) for v in row) for row in self.q)
        active_before = tuple(tuple(bool(v) for v in row) for row in old_active)
        events: list[QUpdate | Elimination] = []
        denominator = (self.holding_rate + self.penalty_rate) * self.capacity

        # A_h^k stays fixed for all stopping-time/feasibility calculations.
        # Future-stage V values use this episode's freshly updated Q values,
        # as in the backward loop in Algorithm 1, before next-episode pruning.
        for start in range(horizon - 1, -1, -1):
            running = np.flatnonzero(old_active[start])
            for action_value in running:
                action = int(action_value)
                stock = action
                reward_sum = 0.0
                bootstrap = 0.0
                stop = horizon + 1
                path = []
                for phase in range(start, horizon):
                    observed = self.buffer[phase]
                    if stock > observed.choice.order_up_to:
                        raise RuntimeError("Quỹ đạo giả định yêu cầu phản hồi mà HQL không quan sát được.")
                    sales = min(stock, observed.sales)
                    remaining = stock - sales
                    reward = (self.holding_rate * self.capacity - self.holding_rate * remaining + self.penalty_rate * sales) / denominator
                    path.append(CounterfactualStep(phase + 1, stock, observed.sales, sales, remaining, reward))
                    reward_sum += reward
                    stock = remaining
                    next_phase = phase + 1
                    if next_phase == horizon:
                        break  # τ = H+1, V_{H+1}=0; no terminal reward.
                    candidates = np.flatnonzero(old_active[next_phase])
                    feasible = candidates[candidates >= stock]
                    if len(feasible):
                        stop = next_phase + 1
                        bootstrap = float(np.max(self.q[next_phase, feasible]))
                        break
                    # Otherwise place no further order in the hypothetical
                    # path and accumulate rewards until feasibility returns.
                old_q = float(self.q[start, action])
                target = reward_sum + bootstrap
                new_q = (1 - alpha) * old_q + alpha * target
                self.q[start, action] = new_q
                events.append(QUpdate(start + 1, action, old_q, alpha, reward_sum, stop, bootstrap, target, new_q, tuple(path)))

            best = int(running[np.argmax(self.q[start, running])])
            best_q = float(self.q[start, best])
            kept = tuple(int(y) for y in running if best_q - self.q[start, y] <= bound + 1e-12)
            removed = tuple(int(y) for y in running if int(y) not in kept)
            self.active[start] = False
            self.active[start, list(kept)] = True
            events.append(Elimination(start + 1, best, best_q, bound, kept, removed))

        return EpisodeTrace(
            episode, alpha, bound, q_before,
            tuple(tuple(float(v) for v in row) for row in self.q), active_before,
            tuple(tuple(bool(v) for v in row) for row in self.active),
            tuple(self.buffer), tuple(events),
        )
