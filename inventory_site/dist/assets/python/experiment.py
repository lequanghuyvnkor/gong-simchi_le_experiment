"""Paired human/HQL rollouts with one shared demand draw per calendar day."""

from hql import HQL
from meta_hql import MetaHQL
from model import Config, DayResult, _integer, sample_demand, simulate_day


class PairedRun:
    def __init__(self, config: Config, confidence_scale: float = 8.0, bandit_c2: float = 1.0):
        self.version = 3
        self.config = config
        self.bandit_c2 = bandit_c2
        self.human: list[DayResult] = []
        self.hql_history: list[DayResult] = []
        self.choices = []
        self.agent = HQL(
            config.capacity, config.holding_rate, config.penalty_rate,
            config.total_days, config.initial_inventory, confidence_scale,
        ) if config.discard_at_cycle_end else MetaHQL(
            config.capacity, config.holding_rate, config.penalty_rate,
            config.total_days, config.initial_inventory, confidence_scale, bandit_c2,
        )

    @property
    def algorithm_name(self) -> str:
        return "HQL" if self.config.discard_at_cycle_end else "Meta-HQL"

    @property
    def inventory(self) -> int:
        return self.human[-1].next_opening if self.human else self.config.initial_inventory

    def step(self, target: int) -> DayResult:
        day = len(self.human) + 1
        _integer("Mức tồn sau bổ sung", target)
        if day > self.config.total_days:
            raise ValueError("Thí nghiệm đã kết thúc.")
        if not self.inventory <= target <= self.config.capacity:
            raise ValueError("Cần tồn đầu ngày ≤ yₜ ≤ M.")
        # Both decisions precede the single shared demand realization.
        choice = self.agent.plan() if self.agent else None
        demand = sample_demand(self.config, day)
        human = simulate_day(self.config, day, self.inventory, target, demand)
        if choice is not None:
            other = simulate_day(self.config, day, choice.opening, choice.order_up_to, demand)
            self.agent.observe(other.sales)  # ONLY the HQL store's own sales.
            if self.agent.inventory != other.next_opening:
                raise RuntimeError("Tồn kho thuật toán và môi trường không khớp.")
            self.choices.append(choice)
            self.hql_history.append(other)
        self.human.append(human)
        return human

    def comparison_rows(self, researcher: bool = False) -> list[dict]:
        rows = []
        if self.agent is None:
            return rows
        human_cost = hql_cost = human_pseudo = hql_pseudo = 0.0
        name = self.algorithm_name
        for human, other in zip(self.human, self.hql_history, strict=True):
            human_cost += human.total_cost
            hql_cost += other.total_cost
            human_pseudo += human.pseudo_cost
            hql_pseudo += other.pseudo_cost
            row = {
                "Ngày": human.day,
                "Chu kỳ": human.cycle,
                "Bạn · tồn đầu": human.opening,
                "HQL · tồn đầu": other.opening,
                "Bạn · mức y": human.order_up_to,
                "HQL · mức y": other.order_up_to,
                "Bạn · đặt thêm": human.ordered,
                "HQL · đặt thêm": other.ordered,
                "Bạn · bán": human.sales,
                "HQL · bán": other.sales,
                "Bạn · chi phí giả định lũy kế": human_pseudo,
                "HQL · chi phí giả định lũy kế": hql_pseudo,
                "Chênh lệch chi phí Bạn − HQL": human_pseudo - hql_pseudo,
                "Phiên bản HQL": self.agent.label,
                "Hệ số cận": self.agent.confidence_scale,
            }
            if researcher:
                row.update({
                    "Nhu cầu chung D": human.demand,
                    "Bạn · chi phí ngày": human.total_cost,
                    "HQL · chi phí ngày": other.total_cost,
                    "Bạn · tổng chi phí": human_cost,
                    "HQL · tổng chi phí": hql_cost,
                    "Bạn · cầu mất": human.lost,
                    "HQL · cầu mất": other.lost,
                })
            if name == "Meta-HQL":
                row = {key.replace("HQL", "Meta-HQL"): value for key, value in row.items()}
                choice = self.choices[human.day - 1]
                row.update({"Bản sao được chọn": choice.arm, "Pha bandit j": choice.bandit_phase,
                            "Ngày nội bộ HQL": choice.local_phase, "Trạng thái Meta-HQL": choice.status,
                            "C₂ bandit": self.bandit_c2})
            rows.append(row)
        return rows
