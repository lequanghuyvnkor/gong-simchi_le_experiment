"""Small, auditable lost-sales environment; no learning policy is assumed."""

from dataclasses import dataclass
from math import isfinite
from numbers import Integral

import numpy as np


CYCLE_LENGTH = 3


def _integer(name: str, value: int, minimum: int = 0) -> None:
    if isinstance(value, bool) or not isinstance(value, Integral) or value < minimum:
        raise ValueError(f"{name} phải là số nguyên từ {minimum} trở lên.")


@dataclass(frozen=True)
class Config:
    capacity: int = 20
    initial_inventory: int = 3
    holding_rate: float = 1.0
    penalty_rate: float = 4.0
    demand_means: tuple[float, float, float] = (4.0, 8.0, 5.0)
    seed: int = 42
    cycles: int = 3
    discard_at_cycle_end: bool = True

    def __post_init__(self) -> None:
        _integer("Mức tồn kho tối đa", self.capacity, 1)
        _integer("Tồn kho ban đầu", self.initial_inventory)
        _integer("Số chu kỳ", self.cycles, 1)
        _integer("Mã tình huống", self.seed)
        if self.initial_inventory > self.capacity:
            raise ValueError("Tồn kho ban đầu phải nhỏ hơn hoặc bằng mức tồn kho tối đa M.")
        for name, value in [("Phí lưu kho", self.holding_rate), ("Mức phạt thiếu hàng", self.penalty_rate)]:
            if not isfinite(value) or value <= 0:
                raise ValueError(f"{name} phải là số dương hữu hạn.")
        if len(self.demand_means) != CYCLE_LENGTH:
            raise ValueError("Cần đúng 3 mức nhu cầu trung bình, tương ứng 3 ngày trong chu kỳ.")
        if any(not isfinite(value) or value < 0 for value in self.demand_means):
            raise ValueError("Nhu cầu trung bình phải là số không âm hữu hạn.")

    @property
    def total_days(self) -> int:
        return CYCLE_LENGTH * self.cycles


@dataclass(frozen=True)
class DayResult:
    day: int
    cycle: int
    phase: int
    opening: int
    order_up_to: int
    ordered: int
    demand: int
    sales: int
    remaining: int
    lost: int
    discarded: int
    next_opening: int
    holding_rate: float
    penalty_rate: float
    holding_cost: float
    penalty_cost: float
    total_cost: float
    pseudo_cost: float

    @property
    def censored(self) -> bool:
        # Equality also censors demand: selling every unit does not establish
        # whether demand equaled stock or exceeded it. This includes y = 0.
        return self.sales == self.order_up_to


def sample_demand(config: Config, day: int) -> int:
    """Draw only the requested day; decisions and UI reruns cannot change it.

    Independent per-day random streams make same-seed replays share exactly
    the same demand path even when order decisions differ.
    """
    _integer("Ngày", day, 1)
    if day > config.total_days:
        raise ValueError("Đã vượt quá số ngày của thí nghiệm.")
    phase = (day - 1) % CYCLE_LENGTH
    rng = np.random.default_rng(np.random.SeedSequence([config.seed, day]))
    return int(rng.poisson(config.demand_means[phase]))


def simulate_day(config: Config, day: int, opening: int, order_up_to: int, demand: int) -> DayResult:
    """Order, fulfill demand, charge costs, then perform the cycle-end reset."""
    for name, value in [("Ngày", day), ("Tồn đầu ngày", opening), ("Mức tồn sau bổ sung", order_up_to), ("Nhu cầu", demand)]:
        _integer(name, value, 1 if name == "Ngày" else 0)
    if day > config.total_days:
        raise ValueError("Thí nghiệm đã kết thúc. Hãy bắt đầu lại để chạy tiếp.")
    if not 0 <= opening <= order_up_to <= config.capacity:
        raise ValueError("Quyết định hợp lệ cần 0 ≤ xₜ ≤ yₜ ≤ M: chỉ bổ sung hàng và giữ tồn kho trong giới hạn M.")

    phase = (day - 1) % CYCLE_LENGTH + 1
    sales = min(order_up_to, demand)
    remaining = order_up_to - sales
    lost = max(demand - order_up_to, 0)
    # Holding cost is charged on post-sales inventory BEFORE any reset.
    # Zero salvage value and zero extra disposal cost are teaching defaults.
    discarded = remaining if config.discard_at_cycle_end and phase == CYCLE_LENGTH else 0
    holding_cost = config.holding_rate * remaining
    penalty_cost = config.penalty_rate * lost
    return DayResult(
        day=day,
        cycle=(day - 1) // CYCLE_LENGTH + 1,
        phase=phase,
        opening=opening,
        order_up_to=order_up_to,
        ordered=order_up_to - opening,
        demand=demand,
        sales=sales,
        remaining=remaining,
        lost=lost,
        discarded=discarded,
        next_opening=remaining - discarded,
        holding_rate=config.holding_rate,
        penalty_rate=config.penalty_rate,
        holding_cost=holding_cost,
        penalty_cost=penalty_cost,
        total_cost=holding_cost + penalty_cost,
        pseudo_cost=holding_cost - config.penalty_rate * sales,
    )


def history_rows(history: list[DayResult], researcher: bool = False) -> list[dict]:
    """Whitelist observed data; never silently export hidden demand or costs."""
    rows = []
    for result in history:
        row = {
            "Ngày": result.day,
            "Chu kỳ": result.cycle,
            "Ngày trong chu kỳ": result.phase,
            "Tồn đầu ngày x": result.opening,
            "Đặt thêm q": result.ordered,
            "Sau bổ sung y": result.order_up_to,
            "Bán được S": result.sales,
            "Tồn sau bán I": result.remaining,
            "Loại bỏ cuối chu kỳ": result.discarded,
            "Tồn sang ngày sau": result.next_opening,
            "Chi phí lưu kho": result.holding_cost,
            "Chi phí giả định": result.pseudo_cost,
            "Quan sát nhu cầu": f"D ≥ {result.sales}" if result.censored else f"D = {result.sales}",
        }
        if researcher:
            row.update({
                "Nhu cầu thật D": result.demand,
                "Nhu cầu mất L": result.lost,
                "Chi phí mất doanh số": result.penalty_cost,
                "Tổng chi phí thật": result.total_cost,
            })
        rows.append(row)
    return rows
