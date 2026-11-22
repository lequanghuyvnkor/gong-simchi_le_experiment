"""Shifted HQL copies under the doubling-phase scheduler of §5 / Algorithm 2.

All observations are this physical store's censored sales. The physical stock
is never discarded. C2 is left unspecified in the paper: 1 is the teaching
default here, rather than a claimed theoretical calibration.
"""

from dataclasses import dataclass, replace
from math import isfinite, log, sqrt

import numpy as np

from hql import EpisodeTrace, HQL, ShiftTrim
from model import CYCLE_LENGTH, _integer


@dataclass(frozen=True)
class MetaChoice:
    day: int
    phase: int
    opening: int
    order_up_to: int
    ordered: int
    arm: int
    local_phase: int | None
    bandit_phase: int
    completed_in_block: int
    block_target: int
    status: str
    entry_cap: int
    starts_block: bool
    eligible_arms: tuple[int, ...] = ()


@dataclass(frozen=True)
class ArmState:
    arm: int
    episodes: int
    value: float
    entry_cap: int
    alive: bool
    selected: bool


@dataclass(frozen=True)
class MetaEvent:
    kind: str
    title: str
    explanation: str


@dataclass(frozen=True)
class ArmAssessment:
    arm: int
    episodes: int
    value: float
    gap: float
    threshold: float
    was_alive: bool
    kept: bool


@dataclass(frozen=True)
class BanditReview:
    day: int
    phase: int
    best_arm: int
    assessments: tuple[ArmAssessment, ...]


@dataclass(frozen=True)
class MetaStep:
    choice: MetaChoice
    sales: int
    remaining: int
    events: tuple[MetaEvent, ...]
    arms_after: tuple[ArmState, ...]
    q_trace: EpisodeTrace | None
    review: BanditReview | None


class MetaHQL:
    def __init__(self, capacity: int, holding_rate: float, penalty_rate: float,
                 total_days: int, initial_inventory: int = 0,
                 confidence_scale: float = 8.0, bandit_c2: float = 1.0):
        if not isfinite(bandit_c2) or bandit_c2 <= 0:
            raise ValueError("C₂ của bandit phải là số dương hữu hạn.")
        self.capacity = capacity
        self.holding_rate = float(holding_rate)
        self.penalty_rate = float(penalty_rate)
        self.total_days = total_days
        self.confidence_scale = float(confidence_scale)
        self.bandit_c2 = float(bandit_c2)
        self.learners = tuple(HQL(capacity, holding_rate, penalty_rate, total_days, 0, confidence_scale) for _ in range(CYCLE_LENGTH))
        _integer("Tồn kho thực ban đầu", initial_inventory)
        if initial_inventory > capacity:
            raise ValueError("Tồn kho ban đầu phải ≤ M.")
        self.inventory = initial_inventory
        self.days_observed = 0
        self.bandit_phase = 0
        self.alive = [True] * CYCLE_LENGTH
        self.current_arm = 1
        self.completed_in_block = 0
        self.visited: set[int] = set()
        self.running = False
        self.steps: list[MetaStep] = []
        self.bandit_reviews: list[BanditReview] = []
        self.safeguard_count = 0

    @property
    def label(self) -> str:
        tag = "Meta-HQL" if self.confidence_scale == 8 and self.bandit_c2 == 1 else "Meta-HQL minh họa"
        return f"{tag} · c₁={self.confidence_scale:g}, C₂={self.bandit_c2:g}"

    def entry_cap(self, arm: int) -> int:
        return int(np.flatnonzero(self.learners[arm - 1].active[0])[-1])

    def states(self) -> tuple[ArmState, ...]:
        return tuple(ArmState(
            arm, len(learner.traces), float(np.max(learner.q[0, learner.active[0]])),
            self.entry_cap(arm), self.alive[arm - 1], arm == self.current_arm,
        ) for arm, learner in enumerate(self.learners, 1))

    def plan(self) -> MetaChoice:
        if self.days_observed >= self.total_days:
            raise ValueError("Meta-HQL đã chạy đủ số ngày.")
        day = self.days_observed + 1
        phase = (day - 1) % CYCLE_LENGTH + 1
        arm = self.current_arm
        learner = self.learners[arm - 1]
        cap = self.entry_cap(arm)
        starts = not self.running
        wrong_phase = starts and phase != arm
        excess_stock = starts and self.inventory > cap
        if wrong_phase or excess_stock:
            status = "wait_both" if wrong_phase and excess_stock else "wait_phase" if wrong_phase else "wait_stock"
            local_phase = None
            target = self.inventory
        else:
            status = "run"
            local_phase = len(learner.buffer) + 1
            top = int(np.flatnonzero(learner.active[local_phase - 1])[-1])
            target = max(self.inventory, top)
        return MetaChoice(day, phase, self.inventory, target, target - self.inventory,
                          arm, local_phase, self.bandit_phase, self.completed_in_block,
                          2**self.bandit_phase, status, cap, starts,
                          tuple(arm for arm in range(1, CYCLE_LENGTH + 1) if self.alive[arm - 1]))

    def _trim(self, arm: int, trace: EpisodeTrace) -> tuple[EpisodeTrace, MetaEvent]:
        learner = self.learners[arm - 1]
        before_trim = learner.active.copy()
        proposed = before_trim.copy()
        cap = self.entry_cap(arm)
        proposed[:, cap + 1:] = False
        restored = False
        if not proposed.any(axis=1).all():
            # The author replication also stops a shifted copy when trimming
            # empties a running set. Preserve its prior nonempty sets for audit.
            proposed = np.array(trace.active_before, dtype=bool)
            restored = True
            if sum(self.alive) > 1:
                self.alive[arm - 1] = False
                message = MetaEvent("retire", f"Ngừng bản sao {arm} do tập ứng viên rỗng", "Giới hạn các mức của ngày nội bộ 2–3 theo trần ngày đầu đã làm rỗng một tập. Bản sao này ngừng được chọn; tồn kho thực vẫn giữ nguyên.")
            else:
                self.safeguard_count += 1
                message = MetaEvent("safeguard", "Giữ tập ứng viên trước của bản sao cuối", "Cận minh họa có thể làm phép chặn tập bị rỗng. Bản học giữ các tập trước cập nhật để tiếp tục ván và ghi rõ lần bảo vệ này; đây là xử lý thực hành, không phải bảo đảm lý thuyết.")
        else:
            message = MetaEvent("trim", f"Chặn mức tồn của bản sao {arm}", f"Sau khi học, trần ngày nội bộ 1 là {cap}. Các ngày nội bộ 2–3 chỉ giữ mức không vượt trần này; ba tập vẫn không rỗng.")
        learner.active[:] = proposed
        trim_events = []
        traced_active = np.array(trace.active_after, dtype=bool)
        for phase in range(CYCLE_LENGTH):
            if not np.array_equal(traced_active[phase], proposed[phase]):
                kept = tuple(int(y) for y in np.flatnonzero(proposed[phase]))
                removed = tuple(int(y) for y in np.flatnonzero(traced_active[phase] & ~proposed[phase]))
                trim_events.append(ShiftTrim(phase + 1, int(np.flatnonzero(proposed[0])[-1]), kept, removed, restored))
        adjusted = replace(trace, active_after=tuple(tuple(bool(v) for v in row) for row in proposed), events=(*trace.events, *trim_events))
        learner.traces[-1] = adjusted
        return adjusted, message

    def _review_bandit(self, day: int) -> BanditReview:
        states = self.states()
        observed = [state for state in states if state.alive and state.episodes > 0]
        best = max(observed, key=lambda state: state.value)
        rows = []
        for state in states:
            # 2*CB2 = 4*C2*sqrt(H^7 log(T) / K_w).
            threshold = 4 * self.bandit_c2 * sqrt(CYCLE_LENGTH**7 * log(self.total_days) / state.episodes) if state.episodes else float("inf")
            gap = best.value - state.value
            eliminate = state.alive and state.arm != best.arm and gap >= threshold
            if eliminate:
                self.alive[state.arm - 1] = False
            rows.append(ArmAssessment(state.arm, state.episodes, state.value, gap, threshold, state.alive, self.alive[state.arm - 1]))
        review = BanditReview(day, self.bandit_phase, best.arm, tuple(rows))
        self.bandit_reviews.append(review)
        return review

    def observe(self, sales: int) -> MetaStep:
        """Accept only the selected physical store's censored sales, even in waits."""
        choice = self.plan()
        _integer("Lượng bán của Meta-HQL", sales)
        if sales > choice.order_up_to:
            raise ValueError("Lượng bán vượt tồn kho sẵn bán của Meta-HQL.")
        self.inventory = choice.order_up_to - sales
        self.days_observed += 1
        events = [MetaEvent("schedule", f"Bandit giao khối cho bản sao {choice.arm}", f"Pha bandit j = {choice.bandit_phase}; các nhánh còn lại W_j = {list(choice.eligible_arms)}. Theo lịch khám phá, mỗi nhánh chạy thêm 2^j = {choice.block_target} tập, mỗi tập 3 ngày. Đang đến bản sao {choice.arm}, đã hoàn tất {choice.completed_in_block} tập trong khối này.")]
        trace = None
        review = None
        if choice.status != "run":
            reasons = []
            if choice.status in ("wait_phase", "wait_both"):
                reasons.append(f"hôm nay là ngày chu kỳ {choice.phase}, cần chờ ngày {choice.arm}")
            if choice.status in ("wait_stock", "wait_both"):
                reasons.append(f"tồn {choice.opening} còn cao hơn trần bắt đầu {choice.entry_cap}")
            events.append(MetaEvent("wait", "Chờ điều kiện chuyển — đặt thêm 0", "; ".join(reasons) + ". Ngày chờ vẫn có khách mua và chi phí, nhưng không huấn luyện bản sao nào."))
            events.append(MetaEvent("feedback", "Giữ toàn bộ hàng còn lại", f"Bán {sales}, còn {self.inventory} sản phẩm chuyển sang ngày sau. Không loại bỏ hàng để ép chuyển bản sao."))
        else:
            self.running = True
            learner = self.learners[choice.arm - 1]
            local = choice.local_phase
            events.append(MetaEvent("entry" if choice.starts_block else "continue", "Bắt đầu khối đúng pha và đủ điều kiện" if choice.starts_block else "Tiếp tục bản sao đang chạy", f"Ngày thực trong chu kỳ = {choice.phase}; ngày nội bộ của bản sao {choice.arm} = {local}. Tồn thực trước bán là {choice.opening}."))
            events.append(MetaEvent("choose", f"HQL {choice.arm} chọn y = {choice.order_up_to}", f"Đang có {choice.opening}, đặt thêm {choice.ordered}. Quy tắc là lấy mức cao nhất còn trong tập ứng viên của ngày nội bộ, hoặc giữ nguyên x nếu tồn đang cao hơn mức đó."))
            # The base episodic learner's virtual reset never changes the real
            # store. Synchronize its starting state only on an executed action.
            learner.inventory = choice.opening
            if learner.plan().order_up_to != choice.order_up_to:
                raise RuntimeError("Kế hoạch bản sao không khớp quyết định Meta-HQL.")
            trace = learner.observe(sales)
            events.append(MetaEvent("feedback", "Chỉ học từ lượng bán riêng", f"Meta-HQL quan sát S = {sales}, tính hàng dư I = {self.inventory}. Bộ học không nhận nhu cầu thật, chi phí thiếu hàng thật hay dữ liệu của cửa hàng thủ công."))
            if trace is not None:
                trace, trimming_event = self._trim(choice.arm, trace)
                self.completed_in_block += 1
                events.append(MetaEvent("learn", f"Cập nhật Q của bản sao {choice.arm}", f"Đã hoàn tất tập riêng thứ {trace.episode} của bản sao, cập nhật ngược h nội bộ = 3, 2, 1 với α = {trace.alpha:.5f}. Tồn thực còn {self.inventory}, không đưa về 0."))
                events.append(trimming_event)
                events.append(MetaEvent("value", "Cập nhật ước lượng giá trị của nhánh", f"V₁ của bản sao {choice.arm} = {self.states()[choice.arm - 1].value:.5f}; bộ đếm mẫu của nhánh là {len(learner.traces)} tập đã hoàn tất."))
                if self.completed_in_block >= choice.block_target or not self.alive[choice.arm - 1]:
                    self.visited.add(choice.arm)
                    self.running = False
                    pending = [arm for arm in range(1, CYCLE_LENGTH + 1) if self.alive[arm - 1] and arm not in self.visited]
                    if not pending:
                        review = self._review_bandit(choice.day)
                        kept = [row.arm for row in review.assessments if row.kept]
                        removed = [row.arm for row in review.assessments if row.was_alive and not row.kept]
                        events.append(MetaEvent("bandit_review", f"Kết thúc pha bandit j = {self.bandit_phase}", f"So sánh V₁ từng nhánh; loại khi kém nhánh tốt nhất ít nhất 2CB₂(K_w). Nhánh tốt nhất hiện tại: {review.best_arm}. Giữ {kept}; loại {removed}."))
                        self.bandit_phase += 1
                        self.visited.clear()
                        pending = kept
                    self.current_arm = pending[0]
                    self.completed_in_block = 0
                    events.append(MetaEvent("switch", f"Xét bản sao {self.current_arm} cho khối kế tiếp", f"Khối vừa chạy của bản sao {choice.arm} đã kết thúc. Từ ngày sau, chờ đúng pha {self.current_arm} và tồn không vượt trần của nhánh mới. Toàn bộ {self.inventory} sản phẩm vẫn thuộc cùng một kho thực."))
        step = MetaStep(choice, sales, self.inventory, tuple(events), self.states(), trace, review)
        self.steps.append(step)
        return step
