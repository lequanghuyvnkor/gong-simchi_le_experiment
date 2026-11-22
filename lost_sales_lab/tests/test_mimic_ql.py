"""Check the declared teaching construction, not the published regret theorem."""
from itertools import product
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mimic_ql
from fql import FQL
from fql_model import FQLConfig, FQLSpec, StockState
from mimic_ql import ContinuousDay, MimicRun, position


@pytest.mark.parametrize("horizon", [6, 9])
def test_artificial_clock_sweeps_all_phases_and_uses_valid_reward_bound(horizon):
    spec = FQLSpec(max_order=(1, 1), demand_cap=1, initial_stock=(0, 0))
    learner = FQL(spec, horizon=horizon)
    for k in (1, 2):
        for h in range(horizon):
            trace = learner.observe((1, h % 2))
            assert (trace is not None) == (h == horizon - 1)
        assert [u.phase for u in trace.updates] == list(range(horizon, 0, -1))
        assert all(u.alpha == (horizon+1)/(horizon+k) for u in trace.updates)
        assert learner.state == spec.initial_state
        assert len(trace.snapshot(horizon)) == horizon
    for grid in learner.grids:
        for demand in product((0, spec.demand_cap), repeat=2):
            net = grid.values[:, :2] + grid.values[:, 2:] - demand
            cost = (np.maximum(net, 0) @ spec.holding + np.maximum(-net, 0) @ spec.backlog_rate)[:, None] + learner._action_cost
            assert cost.min() >= 0 and cost.max() <= learner.cost_bound


def test_physical_balances_survive_both_cycle_and_virtual_reset(monkeypatch):
    monkeypatch.setattr(mimic_ql, "sample_fql_demand", lambda config, day: (2, 1))
    run = MimicRun(FQLConfig(cycles=3))
    for day in range(1, 10):
        previous = run.physical_state
        run.step((0, 0))
        actual = run.algorithm[-1]
        assert actual.next_state == actual.flow.closing
        assert not actual.terminal
        assert actual.flow.opening == previous
        assert actual.flow.closing.net == tuple(n+p-d for n,p,d in zip(previous.net,previous.pipeline,(2,1)))
        assert run.virtual_learner.days_observed == day
        assert run.human[-1].flow.demand == actual.flow.demand == run.virtual[-1].demand
        assert run.explanation()["virtual_reset"] == (day % 6 == 0)
        if day == 6:
            assert run.virtual_learner.state == run.config.spec.initial_state
            assert run.physical_state != run.config.spec.initial_state
    assert run.human_state.net == (-18, -9)
    assert len(run.virtual_learner.traces) == 1
    assert len(run.virtual_learner.pending) == 3


def test_match_includes_virtual_order_and_records_actuator_limit():
    run = MimicRun(FQLConfig())
    # At a virtual reset, outstanding physical debt can exceed the actuator.
    physical = StockState((-10, -7), (1, 0))
    run.algorithm.append(ContinuousDay(1, None, physical))
    choice = run.plan()
    assert position(physical) == (-9, -7)
    assert choice.requested == (9, 7)
    assert choice.executed == (2, 2)
    assert choice.limited == (True, True)
    # A nonzero virtual action is part of the position being matched.
    run.virtual_learner.q[0][0, -1] = 100
    choice = run.plan()
    assert choice.virtual_order == (2, 2)
    assert choice.requested == (11, 9)


def test_human_policy_does_not_enter_virtual_learning_or_algorithm_path():
    a, b = MimicRun(FQLConfig(cycles=3)), MimicRun(FQLConfig(cycles=3))
    for _ in range(9):
        a.step((0, 0)); b.step((2, 2))
    assert a.algorithm == b.algorithm
    assert a.choices == b.choices
    for x, y in zip(a.virtual_learner.q, b.virtual_learner.q):
        np.testing.assert_array_equal(x, y)
    assert not hasattr(a.virtual_learner, "config")
    assert not hasattr(a.virtual_learner.spec, "seed")
    before = len(a.choices)
    with pytest.raises(ValueError):
        a.step((1.5, 0))
    assert len(a.choices) == before
