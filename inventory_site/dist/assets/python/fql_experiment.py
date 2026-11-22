"""Paired human/FQL experiment: one demand vector after both decisions."""

from fql import FQL
from fql_model import FQLConfig, sample_fql_demand, simulate_fql_day, validate_order


class FQLRun:
    def __init__(self, config: FQLConfig):
        self.config = config
        self.agent = FQL(config.spec)
        self.human = []
        self.algorithm = []
        self.choices = []

    @property
    def human_state(self):
        return self.human[-1].next_state if self.human else self.config.spec.initial_state

    def step(self, order):
        order = validate_order(self.config.spec, order)
        day = len(self.human) + 1
        if day > self.config.total_days:
            raise ValueError("Đã chạy đủ số ngày.")
        choice = self.agent.plan()
        demand = sample_fql_demand(self.config, day)
        human = simulate_fql_day(self.config, day, self.human_state, order, demand)
        algorithm = simulate_fql_day(self.config, day, choice.state, choice.order, demand)
        self.agent.observe(demand)
        assert self.agent.state == algorithm.next_state
        self.human.append(human)
        self.algorithm.append(algorithm)
        self.choices.append(choice)
        return human

    def comparison_rows(self):
        rows = []
        totals = {"Bạn": 0.0, "FQL": 0.0}
        for human, algorithm in zip(self.human, self.algorithm):
            row = {"Ngày": human.day, "Chu kỳ": human.cycle, "Ngày trong chu kỳ": human.phase,
                   "Nhu cầu A": human.flow.demand[0], "Nhu cầu B": human.flow.demand[1]}
            for name, result in (("Bạn", human), ("FQL", algorithm)):
                f = result.flow
                for i, product in enumerate(("A", "B")):
                    for label, values in (("tồn đầu", f.opening.on_hand), ("nợ đầu", f.opening.backlog),
                                          ("hàng đến", f.opening.pipeline), ("đặt thêm", f.order),
                                          ("trả nợ cũ", f.old_filled), ("giao cầu mới", f.new_filled),
                                          ("tồn cuối", f.closing.on_hand), ("nợ cuối", f.closing.backlog),
                                          ("đang về cuối", f.closing.pipeline)):
                        row[f"{name} · {product} · {label}"] = values[i]
                for label, value in (("phí đặt chung", f.fixed_cost), ("tiền mua", f.purchase_cost),
                                     ("lưu kho", f.holding_cost), ("chờ giao", f.backlog_cost),
                                     ("chi phí ngày", f.total_cost)):
                    row[f"{name} · {label}"] = value
                totals[name] += f.total_cost
                row[f"{name} · lũy kế"] = totals[name]
            row["Chênh lệch Bạn − FQL"] = totals["Bạn"] - totals["FQL"]
            row["Kết thúc episode"] = human.terminal
            row["Quy ước cuối kỳ"] = "Ghi số dư; V4=0; episode mới độc lập"
            row["Phương pháp"] = "FQL · Algorithm 3 · lưới nguyên hữu hạn"
            row["Seed"] = self.config.seed
            row["Cmax"] = self.config.spec.cost_bound
            row["H"] = 3
            row["L"] = 1
            row["Số chu kỳ thiết lập"] = self.config.cycles
            row["Giới hạn nhu cầu"] = self.config.spec.demand_cap
            row["Phí đặt chung F"] = self.config.spec.fixed_fee
            for i, product in enumerate(("A", "B")):
                for label, values in (("Hạn mức đặt", self.config.spec.max_order),
                                      ("Tồn khởi tạo", self.config.spec.initial_stock),
                                      ("Đơn giá mua", self.config.spec.purchase),
                                      ("Đơn giá lưu", self.config.spec.holding),
                                      ("Đơn giá chờ", self.config.spec.backlog_rate)):
                    row[f"{label} {product}"] = values[i]
                for phase, means in enumerate(self.config.demand_means, start=1):
                    row[f"Cầu trung bình {product} ngày {phase}"] = means[i]
            rows.append(row)
        return rows
