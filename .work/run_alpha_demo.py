"""Reproducible alpha ablation of the workspace's discrete, censored-sales HQL.

Run: python .work/run_alpha_demo.py
The vectorized implementation is checked against lost_sales_lab/hql.py before
experiments. Existing app/source files are not modified.
"""
from __future__ import annotations

import csv
import inspect
import json
import sys
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "alpha_schedule_demo_2026-11-22"
sys.path.insert(0, str(ROOT / "lost_sales_lab"))
import hql as reference

H, M, HOLD, PENALTY = 3, 20, 1.0, 4.0
METHODS = ["HQL", "1/k", "1/k^0.7", "constant_0.05", "constant_0.1"]
LABELS = ["HQL", "1/k", "1/k^0.7", "alpha=0.05", "alpha=0.1"]
SCENARIOS = ["stable_low", "stable_high", "intermittent", "cyclic", "level_shift"]
TITLES = ["Stable, low variation", "Stable, high variation", "Intermittent", "Repeating 3-day cycle", "Level shift halfway"]


def alpha(k, method):
    return {"HQL": (H + 1) / (H + k), "1/k": 1 / k,
            "1/k^0.7": k ** -0.7, "constant_0.05": .05,
            "constant_0.1": .1}[method]


def law(name, phase, after=False):
    if name == "stable_high":
        return np.array([0, 12]), np.array([.5, .5])
    if name == "intermittent":
        return np.array([0, 30]), np.array([.8, .2])
    mean = [4, 10, 6][phase] if name == "cyclic" else (12 if after else 6)
    return np.array([mean - 2, mean, mean + 2]), np.array([.25, .5, .25])


def draw(name, episodes, seeds):
    demand = np.empty((len(seeds), episodes, H), dtype=int)
    for s, seed in enumerate(seeds):
        rng = np.random.default_rng(np.random.SeedSequence([20261122, seed, SCENARIOS.index(name)]))
        u = rng.random((episodes, H))
        for k in range(episodes):
            for h in range(H):
                values, probs = law(name, h, name == "level_shift" and k >= episodes // 2)
                demand[s, k, h] = values[np.searchsorted(probs.cumsum(), u[k, h])]
    return demand


def oracle(name, after=False):
    """Exact finite-horizon DP, independent demand, same grid and end reset."""
    actions = np.arange(M + 1)
    v_cost = np.zeros((H + 1, M + 1))
    q_reward = np.zeros((H, M + 1))
    for h in range(H - 1, -1, -1):
        values, probs = law(name, h, after)
        remain = np.maximum(actions[:, None] - values[None, :], 0)
        lost = np.maximum(values[None, :] - actions[:, None], 0)
        sales = np.minimum(actions[:, None], values[None, :])
        cost_q = ((HOLD * remain + PENALTY * lost + v_cost[h + 1, remain]) * probs).sum(1)
        v_cost[h] = np.minimum.accumulate(cost_q[::-1])[::-1]
        next_v = np.zeros_like(remain, dtype=float)
        if h < H - 1:
            feasible_q = np.maximum.accumulate(q_reward[h + 1, ::-1])[::-1]
            next_v = feasible_q[remain]
        reward = (HOLD * M - HOLD * remain + PENALTY * sales) / ((HOLD + PENALTY) * M)
        q_reward[h] = ((reward + next_v) * probs).sum(1)
    optimal = np.isclose(q_reward, q_reward.max(1, keepdims=True), atol=1e-10, rtol=0)
    return q_reward, optimal, v_cost


class BatchHQL:
    def __init__(self, methods, episodes, scale):
        self.methods, self.episodes, self.scale = methods, episodes, scale
        self.n = len(methods)
        self.q = np.full((self.n, H, M + 1), float(H))
        self.active = np.ones_like(self.q, dtype=bool)
        self.x = np.zeros(self.n, dtype=int)
        self.grid = np.arange(M + 1)[None, :]

    def step(self, demand, k):
        """Environment keeps demand hidden; update receives only own sales."""
        sales_obs = np.empty((self.n, H), dtype=int)
        targets = np.empty_like(sales_obs)
        costs = np.zeros(self.n)
        holding = np.zeros(self.n)
        lost_total = np.zeros(self.n)
        for h in range(H):
            largest = np.where(self.active[:, h], self.grid, -1).max(1)
            y = np.maximum(self.x, largest)
            sales = np.minimum(y, demand[:, h])
            remain = y - sales
            lost = demand[:, h] - sales
            sales_obs[:, h], targets[:, h] = sales, y
            costs += HOLD * remain + PENALTY * lost
            holding += remain
            lost_total += lost
            self.x = remain
        self.x[:] = 0
        delayed, updates = self.update(sales_obs, targets, k)
        return costs, holding, lost_total, delayed, updates

    def update(self, observed, targets, k):
        old = self.active.copy()
        a = np.array([alpha(k, method) for method in self.methods])[:, None]
        bound = np.inf if k == 1 else self.scale * np.sqrt(H**5 * 9 * np.log((M + 1) * self.episodes * H) / (k - 1))
        delayed = np.zeros(self.n)
        counts = np.zeros(self.n)
        for start in range(H - 1, -1, -1):
            running = old[:, start]
            stock = np.broadcast_to(self.grid, (self.n, M + 1)).copy()
            pending = running.copy()
            target = np.zeros_like(stock, dtype=float)
            stopping = np.full_like(stock, H + 1)
            for h in range(start, H):
                if np.any(pending & (stock > targets[:, h, None])):
                    raise AssertionError("Counterfactual exceeds observed feedback support")
                sales = np.minimum(stock, observed[:, h, None])
                remain = stock - sales
                reward = (HOLD * M - HOLD * remain + PENALTY * sales) / ((HOLD + PENALTY) * M)
                target += np.where(pending, reward, 0)
                stock = remain
                if h == H - 1:
                    break
                feasible_values = np.where(old[:, h + 1], self.q[:, h + 1], -np.inf)
                suffix = np.maximum.accumulate(feasible_values[:, ::-1], axis=1)[:, ::-1]
                bootstrap = np.take_along_axis(suffix, stock, axis=1)
                stop_now = pending & np.isfinite(bootstrap)
                target += np.where(stop_now, bootstrap, 0)
                stopping[stop_now] = h + 2
                pending &= ~stop_now
            self.q[:, start] = np.where(running, (1 - a) * self.q[:, start] + a * target, self.q[:, start])
            best = np.where(running, self.q[:, start], -np.inf).max(1)
            self.active[:, start] = running & ((best[:, None] - self.q[:, start]) <= bound + 1e-12)
            delayed += (running & (stopping > start + 2)).sum(1)
            counts += running.sum(1)
        if not self.active.any(2).all() or not np.isfinite(self.q).all():
            raise AssertionError("Invalid running set or nonfinite Q")
        return delayed, counts


def validate():
    """Compare all schedules to existing scalar code; replace alpha in memory."""
    source = textwrap.dedent(inspect.getsource(reference.HQL._update_episode))
    original = "alpha = (horizon + 1) / (horizon + episode)"
    assert source.count(original) == 1
    source = source.replace(original, "alpha = alpha_override(episode)")
    checks = 0
    delayed_seen = False
    for forced in (False, True):
        batch = BatchHQL(METHODS, 120, .01)
        agents = []
        for method in METHODS:
            namespace = dict(vars(reference))
            namespace["alpha_override"] = lambda k, method=method: alpha(k, method)
            exec(compile(source, "<reference-with-alpha-override>", "exec"), namespace)
            cls = type("ReferenceAlpha", (reference.HQL,), {"_update_episode": namespace["_update_episode"]})
            agents.append(cls(M, HOLD, PENALTY, 120 * H, confidence_scale=.01))
        if forced:
            batch.active[:] = False
            batch.active[:, 0, [15, 20]] = True
            batch.active[:, 1:, :5] = True
            for j, agent in enumerate(agents):
                agent.active = batch.active[j].copy()
        rng = np.random.default_rng(8172)
        for k in range(1, 121):
            d = rng.integers(0, 6 if forced else 36, size=H)
            costs, _, _, delayed, _ = batch.step(np.broadcast_to(d, (len(METHODS), H)), k)
            delayed_seen |= bool((delayed > 0).any())
            for j, agent in enumerate(agents):
                cost = 0
                for dem in d:
                    choice = agent.plan()
                    sales = min(choice.order_up_to, int(dem))
                    cost += HOLD * (choice.order_up_to - sales) + PENALTY * (dem - sales)
                    agent.observe(sales)
                np.testing.assert_allclose(batch.q[j], agent.q, atol=1e-12, rtol=1e-12)
                np.testing.assert_array_equal(batch.active[j], agent.active)
                np.testing.assert_allclose(costs[j], cost)
                agent.traces.clear()
                checks += 1
    assert delayed_seen
    # The official schedule must also match the unmodified implementation.
    agent = reference.HQL(M, HOLD, PENALTY, 120 * H, confidence_scale=8)
    batch = BatchHQL(["HQL"], 120, 8)
    for k in range(1, 121):
        d = np.array([4, 9, 6])
        batch.step(d[None], k)
        for dem in d:
            c = agent.plan()
            agent.observe(min(c.order_up_to, int(dem)))
        np.testing.assert_allclose(batch.q[0], agent.q)
        np.testing.assert_array_equal(batch.active[0], agent.active)
    return {"paired_schedule_episode_checks": checks, "unmodified_baseline_checks": 120,
            "forced_delayed_backup_checked": delayed_seen, "passed": True}


def bootstrap_ci(values, rng):
    means = values[rng.integers(0, len(values), size=(4000, len(values)))].mean(1)
    return np.quantile(means, [.025, .975])


def run(episodes=1000, seeds=30):
    OUT.mkdir(parents=True, exist_ok=True)
    verification = validate()
    print("Reference equivalence:", verification, flush=True)
    records, rows = {}, []
    rng_ci = np.random.default_rng(77128)
    for name in SCENARIOS:
        demand = draw(name, episodes, list(range(seeds)))
        before_q, before_opt, _ = oracle(name)
        after_q, after_opt, _ = oracle(name, True) if name == "level_shift" else (before_q, before_opt, None)
        for scale in (8.0, .01):
            mode = "paper_bound" if scale == 8 else "illustrative_bound"
            methods = METHODS * seeds
            batch = BatchHQL(methods, episodes, scale)
            shape = (seeds, len(METHODS), episodes)
            cost, holding, lost, eliminated, qerror, active, delayed, updates = [np.empty(shape) for _ in range(8)]
            for k in range(1, episodes + 1):
                dem = np.repeat(demand[:, k - 1, :], len(METHODS), axis=0)
                c, hold, miss, delay, count = batch.step(dem, k)
                qstar, opt = (after_q, after_opt) if name == "level_shift" and k > episodes // 2 else (before_q, before_opt)
                vals = [c, hold, miss, (~(batch.active & opt).any(2)).mean(1),
                        np.where(batch.active, np.abs(batch.q - qstar), 0).max((1, 2)),
                        batch.active.sum((1, 2)), delay, count]
                for dest, value in zip((cost, holding, lost, eliminated, qerror, active, delayed, updates), vals):
                    dest[:, :, k - 1] = value.reshape(seeds, len(METHODS))
            record = dict(cost=cost, holding=holding, lost=lost, eliminated=eliminated,
                          qerror=qerror, active=active, delayed=delayed, updates=updates, demand=demand)
            records[(name, mode)] = record
            np.savez_compressed(OUT / f"{name}_{mode}.npz", **record)
            per_day = cost.sum(2) / (episodes * H)
            for j, method in enumerate(METHODS):
                diffs = per_day[:, j] - per_day[:, 0]
                lo, hi = bootstrap_ci(diffs, rng_ci)
                rows.append(dict(scenario=name, mode=mode, method=method,
                                 mean_cost_per_day=float(per_day[:, j].mean()),
                                 delta_cost_vs_hql=float(diffs.mean()), delta_ci_low=float(lo), delta_ci_high=float(hi),
                                 mean_cost_first_100=float(cost[:, j, :100].mean() / H),
                                 mean_cost_last_100=float(cost[:, j, -100:].mean() / H),
                                 mean_lost_units_per_day=float(lost[:, j].mean() / H),
                                 mean_held_units_per_day=float(holding[:, j].mean() / H),
                                 mean_final_active_actions=float(active[:, j, -1].mean()),
                                 mean_phase_fraction_without_optimal=float(eliminated[:, j].mean()),
                                 final_phase_fraction_without_optimal=float(eliminated[:, j, -1].mean()),
                                 final_q_max_abs_error_active=float(qerror[:, j, -1].mean()),
                                 delayed_update_fraction=float(delayed[:, j].sum() / updates[:, j].sum())))
            print(name, mode, "cost/day:", np.round(per_day.mean(0), 3),
                  "final candidates:", active[:, :, -1].mean(0), flush=True)
            if scale == 8:
                np.testing.assert_array_equal(cost, np.repeat(cost[:, :1, :], len(METHODS), axis=1))
    with (OUT / "summary.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    config = dict(episodes=episodes, seeds=list(range(seeds)), H=H, capacity=M,
                  holding_cost=HOLD, shortage_penalty=PENALTY, methods=METHODS,
                  confidence_scales=[8, .01], verification=verification,
                  demand_definition={name: [dict(values=law(name, h)[0].tolist(), probabilities=law(name, h)[1].tolist()) for h in range(H)] for name in SCENARIOS},
                  shift_definition="At episode 501, demand support changes to [10,12,14] with p=[.25,.5,.25].",
                  evaluation="Online learning from scratch, paired demand; no parameter search or test-set tuning.",
                  model="Discrete teaching HQL; sales-only feedback; inventory reset to zero each 3-day episode; no procurement cost, disposal cost, or salvage value.",
                  caveat="Scale .01 is a fixed illustrative threshold without theoretical guarantees. All schedules share it. No claim of optimal tuning.")
    (OUT / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    plot_results(records, rows, episodes)
    write_report(rows, config)
    print("Saved:", OUT, flush=True)


def plot_results(records, rows, episodes):
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    colors = ["#233b6e", "#da6a32", "#408b55", "#9371b0", "#cc4b70"]
    fig, axes = plt.subplots(2, 5, figsize=(19, 7), sharex=True)
    for col, (name, title) in enumerate(zip(SCENARIOS, TITLES)):
        for row, mode in enumerate(("paper_bound", "illustrative_bound")):
            data = records[(name, mode)]["cost"]
            ax = axes[row, col]
            for j in range(len(METHODS)):
                smooth = np.array([np.convolve(x, np.ones(50) / 50, mode="valid") for x in data[:, j] / H])
                ax.plot(np.arange(50, episodes + 1), smooth.mean(0), color=colors[j], label=LABELS[j], lw=1.7)
            ax.set_title(title if row == 0 else "")
            ax.grid(alpha=.2)
            if col == 0:
                ax.set_ylabel(("Paper threshold (8)" if row == 0 else "Illustrative threshold (0.01)") + "\nMean cost/day")
            if row == 1:
                ax.set_xlabel("Episode")
            if name == "level_shift":
                ax.axvline(episodes // 2, color="black", ls=":", alpha=.5)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Changing alpha in censored-sales HQL | 30 paired paths, 1,000 episodes, H=3\n50-episode rolling means; lower cost is better. Paper-threshold curves overlap exactly.")
    fig.tight_layout(rect=(0, 0, 1, .92))
    fig.savefig(OUT / "learning_curves.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, 5, figsize=(17, 4.5))
    for ax, name, title in zip(axes, SCENARIOS, TITLES):
        selected = [r for r in rows if r["scenario"] == name and r["mode"] == "illustrative_bound"]
        for j, r in enumerate(selected):
            x, lo, hi = r["delta_cost_vs_hql"], r["delta_ci_low"], r["delta_ci_high"]
            ax.errorbar(x, j, xerr=[[max(0, x-lo)], [max(0, hi-x)]], fmt="o", color=colors[j], capsize=4)
        ax.axvline(0, color="gray", ls="--")
        ax.set_yticks(range(len(METHODS)), LABELS)
        ax.invert_yaxis()
        ax.set_title(title)
        ax.set_xlabel("Cost/day minus HQL")
        ax.grid(axis="x", alpha=.2)
    fig.suptitle("Illustrative threshold only: negative values beat HQL alpha\nPaired mean differences with 95% bootstrap intervals across 30 independent demand paths")
    fig.tight_layout(rect=(0, 0, 1, .87))
    fig.savefig(OUT / "paired_comparison.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for ax, name, title in zip(axes, ["stable_low", "level_shift"],
                               ["Nhu cầu ổn định", "Nhu cầu tăng từ chu kỳ 501"]):
        data = records[(name, "illustrative_bound")]["cost"]
        for j in range(len(METHODS)):
            curve = np.convolve(data[:, j].mean(0) / H, np.ones(50)/50, mode="valid")
            ax.plot(np.arange(50, episodes+1), curve, color=colors[j], label=LABELS[j], lw=2)
        ax.set_title(title)
        ax.set_xlabel("Chu kỳ học")
        ax.set_ylabel("Chi phí trung bình/ngày (thấp hơn = tốt hơn)")
        ax.grid(alpha=.2)
        if name == "level_shift":
            ax.axvline(episodes//2, color="gray", ls=":")
    axes[0].legend(fontsize=9)
    fig.suptitle("Ví dụ với ngưỡng loại bỏ nhỏ hơn (hệ số 0,01)\nTrung bình 30 lần chạy; đường được làm mượt trên 50 chu kỳ")
    fig.tight_layout(rect=(0, 0, 1, .87))
    fig.savefig(OUT / "vi_example.png", dpi=160)
    plt.close(fig)


def write_report(rows, config):
    import html
    table_rows = []
    for name, title in zip(SCENARIOS, TITLES):
        selected = [r for r in rows if r["scenario"] == name and r["mode"] == "illustrative_bound"]
        table_rows.append("<tr><th>" + html.escape(title) + "</th>" + "".join(f"<td>{r['mean_cost_per_day']:.3f}</td>" for r in selected) + "</tr>")
    document = '''<!doctype html><html lang="vi"><meta charset="utf-8"><title>Thí nghiệm alpha của HQL</title>
<style>body{font:17px/1.65 system-ui;max-width:1200px;margin:40px auto;padding:0 24px;color:#203044}table{border-collapse:collapse;width:100%}th,td{padding:10px;border-bottom:1px solid #ccd5e0;text-align:left}img{width:100%;margin:20px 0}.note{background:#f0f4f9;padding:18px;border-radius:10px}code{background:#edf0f5;padding:2px 5px}</style>
<h1>So sánh 5 cách chọn alpha trong HQL</h1>
<p>Đã chạy 5 kịch bản × 5 công thức × 30 chuỗi nhu cầu × 1.000 chu kỳ, cho mỗi ngưỡng loại bỏ. Mỗi chu kỳ 3 ngày; sức chứa 20; phí lưu kho 1/đơn vị/ngày; phạt thiếu hàng 4/đơn vị. Đo tổng chi phí lưu kho và thiếu hàng, càng thấp càng tốt.</p>
<p>Thuật toán chỉ thấy lượng bán được; nhu cầu thật chỉ được bộ mô phỏng dùng để chấm điểm. Hàng còn lại bị loại bỏ cuối mỗi chu kỳ; không có chi phí đặt hàng, giá trị thu hồi hoặc phí hủy bổ sung. Không áp dụng trực tiếp cho mô hình giữ hàng qua chu kỳ.</p>
<div class="note"><b>Kết quả với ngưỡng gốc:</b> Cả 5 công thức ra cùng quyết định và cùng chi phí. Trong 1.000 chu kỳ, ngưỡng lý thuyết quá rộng để loại hành động, nên HQL luôn đặt lên sức chứa 20. Điểm Q khác nhau nhưng quyết định chưa khác.</div>
<p>Để minh họa tác động của alpha, chạy thêm cùng thí nghiệm với hệ số ngưỡng 0,01 thay vì 8. Đây là biến thể minh họa, không có bảo đảm của bài báo. Hệ số này được cố định trước khi chạy kết quả chính và dùng chung cho 5 công thức; chưa tinh chỉnh tối ưu cho từng công thức.</p>
<h2>Những điều quan sát được</h2>
<ul><li>Với nhu cầu ổn định ít nhiễu, alpha cố định 0,1 giảm chi phí từ 8,798 xuống 8,108, khoảng 7,8%, so với alpha HQL cùng ngưỡng minh họa.</li>
<li>Với nhu cầu thưa, chênh lệch nhỏ và các khoảng tin cậy của chênh lệch đều chứa 0; chưa đủ bằng chứng chọn phương án tốt hơn HQL.</li>
<li>Trong kịch bản đổi mức, alpha 0,1 có tổng chi phí thấp hơn nhưng chi phí ở 100 chu kỳ cuối lại cao hơn: 2,221 so với 2,009 của HQL. Khi đó 82,2% cặp lần-chạy/ngày-trong-chu-kỳ không còn hành động tối ưu mới trong Running Set. Con số này là tỷ lệ trên 30 lần chạy × 3 ngày, không phải tỷ lệ ngày thiếu hàng. Tập chỉ thu hẹp và không khôi phục hành động; vì vậy thay alpha đơn lẻ không bảo đảm thích nghi tốt khi demand đổi.</li></ul>
<img src="vi_example.png" alt="Hai ví dụ đường học">
<h2>Chi phí trung bình mỗi ngày — ngưỡng minh họa</h2><table><thead><tr><th>Demand</th>'''
    document += "".join(f"<th>{html.escape(label)}</th>" for label in LABELS) + "</tr></thead><tbody>" + "".join(table_rows) + "</tbody></table>"
    document += '''<img src="paired_comparison.png" alt="Chênh lệch chi phí so với HQL"><p>Biểu đồ trên: chấm nằm bên trái 0 nghĩa là chi phí thấp hơn HQL cùng ngưỡng. Thanh ngang là khoảng tin cậy bootstrap 95% của chênh lệch theo cặp. Các khoảng này chưa điều chỉnh cho việc so sánh nhiều phương án.</p>
<img src="learning_curves.png" alt="Đường học theo chu kỳ"><p>Hàng trên dùng ngưỡng gốc 8, hàng dưới dùng ngưỡng minh họa 0,01. Các đường là chi phí/ngày trung bình trượt trên 50 chu kỳ. Đường dọc ở chu kỳ 500 đánh dấu thay đổi demand. Không khởi động lại thuật toán sau thay đổi.</p>
<h2>Các kịch bản</h2><ul><li>Ổn định ít nhiễu: demand 4, 6, 8 với xác suất 25%, 50%, 25%.</li><li>Ổn định nhiều nhiễu: demand 0 hoặc 12, mỗi mức 50%.</li><li>Nhu cầu thưa: 80% ngày bằng 0, 20% ngày bằng 30. Ba kịch bản này đều có trung bình 6.</li><li>Chu kỳ: trung bình từng ngày là 4, 10, 6; mỗi ngày có ba mức quanh trung bình, lặp lại cùng phân phối giữa các chu kỳ.</li><li>Đổi mức: từ chu kỳ 501, ba mức 4, 6, 8 chuyển thành 10, 12, 14; giữ nguyên xác suất. Đây là stress test ngoài giả định phân phối lặp lại giữa các chu kỳ.</li></ul>
<h2>Kiểm tra tính đúng</h2><p>Bản chạy theo lô đã khớp Q, Running Set và chi phí với mã HQL đang có cho cả 5 lịch alpha qua 1.200 phép đối chiếu theo chu kỳ, có tình huống buộc Delayed Bellman đi qua nhiều ngày. Riêng alpha gốc còn khớp 120 chu kỳ với bản HQL không thay đổi. Bộ chấm tính hành động tối ưu bằng quy hoạch động chính xác trên cùng lưới để theo dõi việc loại nhầm; đáp án này không đưa vào thuật toán học.</p>
<p>Đây là thử nghiệm online từ đầu, chưa tìm tham số tốt nhất và chưa dùng dữ liệu bán hàng thực tế. Không kết luận công thức thắng trong ví dụ sẽ thắng ở mọi ngành hàng. Bộ mô phỏng dùng lưới nguyên 0..20 của ứng dụng giảng dạy hiện có, không phải tái lập đầy đủ gói thí nghiệm của tác giả.</p>
<p>Tệp: <a href="summary.csv">Bảng kết quả CSV</a> · <a href="config.json">Cấu hình và kiểm tra</a>. Mỗi tệp NPZ lưu kết quả từng chu kỳ và chuỗi demand để tái kiểm tra.</p></html>'''
    (OUT / "report.html").write_text(document, encoding="utf-8")


if __name__ == "__main__":
    run()
