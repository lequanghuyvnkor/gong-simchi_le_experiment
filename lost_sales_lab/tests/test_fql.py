from dataclasses import replace
from itertools import product
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fql_experiment
from fql import FQL
from fql_experiment import FQLRun
from fql_model import FQLConfig, FQLSpec, StockState, flow, sample_fql_demand, simulate_fql_day


def test_orders_arrive_tomorrow_and_backlog_is_filled_before_new_demand():
    spec = FQLSpec(initial_stock=(0, 0))
    first = flow(spec, spec.initial_state, (3, 2), (2, 1))
    assert first.new_filled == (0, 0)
    assert first.closing == StockState((-2, -1), (3, 2))
    second = flow(spec, first.closing, (0, 0), (1, 3))
    assert second.old_filled == (2, 1)
    assert second.new_filled == (1, 1)
    assert second.closing == StockState((0, -2), (0, 0))
    assert second.backlog_cost == 10


def test_joint_fee_is_once_per_order_and_purchase_is_paid_before_delivery():
    spec = FQLSpec()
    both = flow(spec, spec.initial_state, (2, 3), (0, 0))
    assert both.fixed_cost == spec.fixed_fee
    assert both.purchase_cost == 2 * spec.purchase[0] + 3 * spec.purchase[1]
    assert both.holding_cost == 1
    assert both.closing.on_hand == spec.initial_stock
    assert flow(spec, spec.initial_state, (0, 0), (0, 0)).fixed_cost == 0


def test_material_balance_without_silent_clipping_for_inventory_and_backlog():
    spec = FQLSpec()
    rng = np.random.default_rng(17)
    for _ in range(150):
        state = StockState(tuple(rng.integers(-20, 21, size=2)), tuple(rng.integers(0, 4, size=2)))
        demand = tuple(rng.integers(0, 5, size=2))
        order = tuple(rng.integers(0, 4, size=2))
        f = flow(spec, state, order, demand)
        for i in range(2):
            assert f.closing.net[i] == state.net[i] + state.pipeline[i] - demand[i]
            assert f.closing.on_hand[i] * f.closing.backlog[i] == 0
            assert f.old_filled[i] + f.new_filled[i] <= state.on_hand[i] + state.pipeline[i]
            assert f.closing.backlog[i] == state.backlog[i] + demand[i] - f.old_filled[i] - f.new_filled[i]


def test_terminal_ledger_keeps_balances_and_next_episode_restarts_explicitly():
    config = FQLConfig()
    state = StockState((-3, 4), (1, 0))
    day = simulate_fql_day(config, 3, state, (2, 3), (1, 2))
    assert day.terminal
    assert day.flow.closing == StockState((-3, 2), (2, 3))
    assert day.flow.backlog_cost == 12
    assert day.flow.purchase_cost == 6.5
    assert day.next_state == config.spec.initial_state


@pytest.mark.parametrize("order,demand", [((-1, 0), (0, 0)), ((4, 0), (0, 0)), ((1.2, 0), (0, 0)), ((True, 0), (0, 0)), ((0, 0), (5, 0)), ((0, 0), (-1, 0))])
def test_invalid_orders_and_out_of_support_demands_raise(order, demand):
    spec = FQLSpec()
    with pytest.raises(ValueError):
        flow(spec, spec.initial_state, order, demand)


def test_grids_contain_every_successor_of_every_reachable_state_and_action():
    agent = FQL(FQLSpec(max_order=(1, 2), demand_cap=2))
    for phase in range(2):
        grid = agent.grids[phase]
        for demand in product(range(3), repeat=2):
            net = grid.values[:, :2] + grid.values[:, 2:] - np.array(demand)
            indices = agent.grids[phase + 1].next_indices(net, agent.actions)
            successors = agent.grids[phase + 1].values[indices]
            np.testing.assert_equal(successors[:, :, :2], np.broadcast_to(net[:, None, :], successors[:, :, :2].shape))
            np.testing.assert_equal(successors[:, :, 2:], np.broadcast_to(agent.actions, successors[:, :, 2:].shape))


def scalar_reference(agent, old, demands, k):
    # Independent Bellman implementation using the business transition function.
    expected = [np.array(q, copy=True) for q in old]
    alpha = 4 / (3 + k)
    for phase in (2, 1, 0):
        for row in range(len(agent.grids[phase].values)):
            state = agent.grids[phase].state(row)
            for index, action in enumerate(agent.actions):
                f = flow(agent.spec, state, tuple(action), demands[phase])
                reward = 1 - f.total_cost / agent.spec.cost_bound
                bootstrap = 0 if phase == 2 else max(expected[phase + 1][agent.grids[phase + 1].index(f.closing)])
                expected[phase][row, index] = (1-alpha) * old[phase][row, index] + alpha * (reward + bootstrap)
    return expected


def test_full_feedback_backward_updates_every_q_entry_with_fresh_next_stage_values():
    agent = FQL(FQLSpec(max_order=(1, 1), initial_stock=(0, 0), demand_cap=2))
    for k, demands in enumerate((((1, 2), (2, 0), (1, 1)), ((0, 2), (1, 1), (2, 0))), start=1):
        before = [q.copy() for q in agent.q]
        expected = scalar_reference(agent, before, demands, k)
        for i, demand in enumerate(demands):
            trace = agent.observe(demand)
            if i < 2:
                assert trace is None
                for old, q in zip(before, agent.q):
                    np.testing.assert_equal(old, q)
        assert [u.phase for u in trace.updates] == [3, 2, 1]
        for q, correct in zip(agent.q, expected):
            np.testing.assert_allclose(q, correct, rtol=0, atol=1e-12)
        assert all(u.alpha == 4 / (3 + k) for u in trace.updates)
        assert agent.state == agent.spec.initial_state
    assert np.count_nonzero(agent.q[2] != 3) == agent.q[2].size  # even unvisited states/actions


def test_hand_calculated_terminal_q_and_lexicographic_ties():
    spec = FQLSpec(max_order=(1, 1), initial_stock=(0, 0), demand_cap=1,
                   purchase=(1, 2), holding=(1, 1), backlog_rate=(3, 4), fixed_fee=2)
    agent = FQL(spec)
    assert agent.plan().order == (0, 0)
    assert agent.plan().tie_count == 4
    for demand in ((0, 0), (1, 0), (1, 1)):
        agent.observe(demand)
    state = StockState((-1, 0), (1, 1))
    row = agent.grids[2].index(state)
    # End net (-1,0); cost no-order=3, joint(1,1)=3+1+2+2=8.
    assert agent.q[2][row, 0] == pytest.approx(1 - 3 / spec.cost_bound)
    assert agent.q[2][row, 3] == pytest.approx(1 - 8 / spec.cost_bound)
    assert np.argmax(agent.q[2][row]) == 0


def test_reward_is_bounded_over_the_entire_reachable_domain():
    spec = FQLSpec(max_order=(4, 3), initial_stock=(5, 0), holding=(100, .5), backlog_rate=(0, 20))
    agent = FQL(spec)
    for grid in agent.grids:
        for demand in product((0, spec.demand_cap), repeat=2):
            net = grid.values[:, :2] + grid.values[:, 2:] - np.array(demand)
            base = np.maximum(net, 0) @ spec.holding + np.maximum(-net, 0) @ spec.backlog_rate
            cost = base[:, None] + agent._action_cost
            assert cost.min() >= 0
            assert cost.max() <= spec.cost_bound


def test_replay_is_read_only_and_snapshots_match_backward_sweep():
    agent = FQL(FQLSpec(max_order=(1, 1), demand_cap=1))
    for _ in range(3):
        agent.observe((1, 1))
    trace = agent.traces[0]
    actual = [q.copy() for q in agent.q]
    for count in range(4):
        snapshot = trace.snapshot(count)
        for phase, q in enumerate(snapshot, start=1):
            update = next(u for u in trace.updates if u.phase == phase)
            np.testing.assert_equal(q, update.q_after if phase > 3-count else update.q_before)
            assert not q.flags.writeable
    for q, old in zip(agent.q, actual):
        np.testing.assert_equal(q, old)
    assert agent.days_observed == 3


def test_one_shared_demand_draw_after_both_decisions_and_validation_before_sampling(monkeypatch):
    run = FQLRun(FQLConfig())
    calls = []
    def draw(config, day):
        calls.append(day)
        assert len(run.human) == day-1
        assert run.agent.days_observed == day-1
        return (4, 2)
    monkeypatch.setattr(fql_experiment, "sample_fql_demand", draw)
    with pytest.raises(ValueError):
        run.step((99, 0))
    assert not calls
    result = run.step((2, 3))
    assert calls == [1]
    assert result.flow.demand == run.algorithm[-1].flow.demand == (4, 2)
    assert run.choices[0].order == (0, 0)


def test_human_orders_cannot_change_algorithm_learning_or_common_demand():
    a, b = FQLRun(FQLConfig()), FQLRun(FQLConfig())
    for _ in range(a.config.total_days):
        a.step((0, 0))
        b.step((3, 3))
    assert a.choices == b.choices
    assert a.algorithm == b.algorithm
    assert [d.flow.demand for d in a.human] == [d.flow.demand for d in b.human]
    for first, second in zip(a.agent.q, b.agent.q):
        np.testing.assert_equal(first, second)
    assert not hasattr(a.agent, "config")
    assert not hasattr(a.agent.spec, "seed")
    assert not hasattr(a.agent.spec, "demand_means")


def test_replay_same_seed_and_csv_accounting_include_terminal_pipeline_and_all_costs():
    run = FQLRun(FQLConfig(cycles=1))
    for _ in range(3):
        run.step((2, 1))
    rows = run.comparison_rows()
    assert rows[-1]["Bạn · A · đang về cuối"] == 2
    assert rows[-1]["Kết thúc episode"]
    assert rows[-1]["Bạn · lũy kế"] == sum(d.flow.total_cost for d in run.human)
    assert rows[-1]["Chênh lệch Bạn − FQL"] == sum(d.flow.total_cost for d in run.human) - sum(d.flow.total_cost for d in run.algorithm)
    assert [sample_fql_demand(run.config, day) for day in range(1, 4)] == [d.flow.demand for d in run.human]
    before = len(run.agent.traces)
    with pytest.raises(ValueError):
        run.step((0, 0))
    assert len(run.agent.traces) == before


def test_zero_cost_and_bad_demand_settings_are_rejected():
    with pytest.raises(ValueError):
        FQLSpec(purchase=(0, 0), holding=(0, 0), backlog_rate=(0, 0), fixed_fee=0)
    with pytest.raises(ValueError):
        replace(FQLConfig(), demand_means=((1, 2), (5, 0), (1, 2)))
