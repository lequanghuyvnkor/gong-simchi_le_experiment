import copy
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiment import PairedRun
from hql import Elimination, HQL, QUpdate
from model import Config


def test_paper_rule_chooses_largest_running_action_even_if_q_argmax_is_smaller():
    agent = HQL(5, 1, 4, 9)
    agent.q[0, 2] = 20
    choice = agent.plan()
    assert choice.order_up_to == 5
    assert choice.best_q_action == 2
    agent.active[0, 4:] = False
    agent.inventory = 4
    choice = agent.plan()
    assert choice.order_up_to == 4
    assert choice.ordered == 0
    assert choice.running == (0, 1, 2, 3)


def test_q_waits_for_cycle_end_and_matches_hand_calculated_backward_update():
    agent = HQL(2, 1, 1, 9)
    assert agent.observe(1) is None
    np.testing.assert_equal(agent.q, 3)
    assert agent.observe(0) is None
    np.testing.assert_equal(agent.q, 3)
    trace = agent.observe(0)
    # Demand [1,0,0], reward (M-I+S)/(2M), backward V=max over feasible y.
    np.testing.assert_allclose(agent.q, [[1.5, 1.75, 1], [1, .5, 0], [.5, .25, 0]])
    assert trace.alpha == 1
    assert trace.bound == float("inf")
    assert agent.active.all()
    assert agent.inventory == 0
    assert [event.phase for event in trace.events if isinstance(event, Elimination)] == [3, 2, 1]


def test_delayed_bellman_waits_until_running_set_becomes_feasible():
    agent = HQL(6, 1, 4, 9)
    agent.active[:] = False
    agent.active[0, [4, 6]] = True
    agent.active[1:, [0, 1]] = True
    for _ in range(3):
        agent.observe(0)
    trace = agent.traces[0]
    event = next(e for e in trace.events if isinstance(e, QUpdate) and e.phase == 1 and e.action == 4)
    assert event.stopping_phase == 4
    assert len(event.trajectory) == 3
    assert event.bootstrap == 0
    assert event.reward_sum == pytest.approx(.2)
    assert event.new_q == pytest.approx(.2)
    assert trace.observations[1].choice.ordered == 0
    assert trace.observations[1].choice.order_up_to == 6


def test_read_only_replay_reproduces_final_q_and_elimination_without_retraining():
    agent = HQL(6, 1, 4, 12, confidence_scale=.001)
    for _ in range(6):
        choice = agent.plan()
        agent.observe(min(choice.order_up_to, 2))
    trace = agent.traces[-1]
    assert any(isinstance(event, Elimination) and event.removed for event in trace.events)
    before = copy.deepcopy(agent)
    q, active = trace.snapshot(len(trace.events))
    np.testing.assert_allclose(q, trace.q_after)
    np.testing.assert_equal(active, trace.active_after)
    for position in range(len(trace.events) + 1):
        trace.snapshot(position)
    np.testing.assert_equal(agent.q, before.q)
    np.testing.assert_equal(agent.active, before.active)
    assert agent.days_observed == before.days_observed
    assert len(agent.traces) == len(before.traces)


def test_alpha_and_paper_confidence_bound_use_episode_index():
    agent = HQL(3, 1, 4, 9)
    for _ in range(6):
        agent.observe(0)
    trace = agent.traces[-1]
    assert trace.alpha == pytest.approx(4 / 5)
    assert trace.bound == pytest.approx(8 * np.sqrt(3**5 * 9 * np.log(4 * 9)))


def test_single_draw_shared_by_both_policies_and_invalid_order_draws_nothing(monkeypatch):
    days = []
    def demand(config, day):
        days.append(day)
        return [8, 1, 7][(day - 1) % 3]
    monkeypatch.setattr("experiment.sample_demand", demand)
    run = PairedRun(Config())
    with pytest.raises(ValueError):
        run.step(2)
    assert days == []
    for _ in range(3):
        run.step(5)
    assert days == [1, 2, 3]
    assert [r.demand for r in run.human] == [r.demand for r in run.hql_history] == [8, 1, 7]
    for record in run.comparison_rows(True):
        assert record["Bạn · tổng chi phí"] - record["HQL · tổng chi phí"] == pytest.approx(record["Chênh lệch chi phí Bạn − HQL"])


def test_hql_learning_does_not_depend_on_human_actions_or_hidden_excess_demand(monkeypatch):
    config = Config(initial_inventory=0, cycles=3)
    monkeypatch.setattr("experiment.sample_demand", lambda cfg, day: 100)
    first = PairedRun(config)
    for _ in range(9):
        first.step(0)
    monkeypatch.setattr("experiment.sample_demand", lambda cfg, day: 200)
    second = PairedRun(config)
    for _ in range(9):
        second.step(20)
    np.testing.assert_allclose(first.agent.q, second.agent.q)
    np.testing.assert_equal(first.agent.active, second.agent.active)
    assert first.choices == second.choices
    assert first.agent.traces == second.agent.traces
    assert first.hql_history[-1].total_cost != second.hql_history[-1].total_cost


def test_many_episodes_preserve_one_sided_feedback_and_nonempty_running_sets():
    run = PairedRun(Config(cycles=20), confidence_scale=.001)
    for _ in range(60):
        run.step(max(run.inventory, 5))
    assert np.isfinite(run.agent.q).all()
    assert run.agent.active.any(axis=1).all()
    assert all(h.demand == q.demand for h, q in zip(run.human, run.hql_history))
    for trace in run.agent.traces:
        for event in trace.events:
            if isinstance(event, QUpdate):
                assert all(0 <= step.reward <= 1 for step in event.trajectory)
                assert event.new_q == pytest.approx((1 - event.alpha) * event.old_q + event.alpha * (event.reward_sum + event.bootstrap))


def test_nondiscarding_selects_meta_hql_instead_of_plain_episodic_hql():
    from meta_hql import MetaHQL
    run = PairedRun(Config(discard_at_cycle_end=False))
    run.step(5)
    assert isinstance(run.agent, MetaHQL)
    assert len(run.hql_history) == 1
    assert "Meta-HQL · mức y" in run.comparison_rows()[0]


def test_observable_comparison_does_not_export_true_demands_or_absolute_true_costs():
    run = PairedRun(Config())
    run.step(5)
    row = run.comparison_rows()[0]
    assert "Nhu cầu chung D" not in row
    assert "Bạn · tổng chi phí" not in row
    assert "HQL · tổng chi phí" not in row
