import copy
from math import log, sqrt
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiment import PairedRun
from hql import ShiftTrim
from meta_hql import MetaHQL
from model import Config


def learner(total_days=36, **kwargs):
    return MetaHQL(5, 1, 4, total_days, initial_inventory=2, **kwargs)


def execute(agent, demand=1):
    choice = agent.plan()
    step = agent.observe(min(choice.order_up_to, demand))
    return step


def test_three_shifted_copies_and_wait_days_keep_one_physical_inventory():
    agent = learner()
    for _ in range(11):
        step = execute(agent)
        assert agent.inventory == step.remaining
        if step.choice.status == "run":
            assert step.choice.phase == (step.choice.arm + step.choice.local_phase - 2) % 3 + 1
    assert [s.choice.arm for s in agent.steps] == [1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3]
    assert [s.choice.day for s in agent.steps if s.choice.status != "run"] == [4, 8]
    assert agent.steps[2].remaining == 4
    assert agent.steps[3].choice.opening == 4
    assert agent.steps[3].choice.ordered == 0
    assert [len(base.traces) for base in agent.learners] == [1, 1, 1]
    assert agent.bandit_phase == 1
    assert len(agent.bandit_reviews) == 1
    assert not np.shares_memory(agent.learners[0].q, agent.learners[1].q)


def test_switch_waits_for_both_correct_phase_and_sufficiently_low_stock():
    agent = learner()
    for _ in range(3):
        execute(agent)
    target_copy = agent.learners[1]
    target_copy.active[:, 3:] = False
    expected = [("wait_both", 0), ("wait_stock", 1), ("wait_both", 1), ("wait_phase", 1)]
    for status, sales in expected:
        choice = agent.plan()
        assert choice.status == status
        assert choice.ordered == 0
        before = target_copy.q.copy()
        agent.observe(sales)
        np.testing.assert_equal(target_copy.q, before)
        assert target_copy.days_observed == 0
    choice = agent.plan()
    assert choice.day == 8
    assert choice.phase == 2
    assert choice.status == "run"
    assert choice.opening == 1
    assert choice.entry_cap == 2


def test_doubling_blocks_are_contiguous_and_copy_learning_does_not_restart():
    agent = learner()
    for _ in range(12):
        execute(agent)
    assert agent.plan().day == 13
    first_copy_q = agent.learners[0].q.copy()
    assert len(agent.learners[0].traces) == 1
    for _ in range(6):
        step = execute(agent)
        assert step.choice.arm == 1
        assert step.choice.status == "run"
        assert step.choice.block_target == 2
    assert len(agent.learners[0].traces) == 3
    assert agent.learners[0].traces[1].alpha == pytest.approx(.8)
    np.testing.assert_equal(agent.learners[0].traces[1].q_before, first_copy_q)
    assert agent.current_arm == 2
    assert not agent.running


def test_internal_episode_boundary_does_not_force_a_new_switch_wait():
    agent = learner()
    agent.bandit_phase = 1
    agent.completed_in_block = 1
    agent.running = True
    agent.days_observed = 3
    agent.inventory = 4
    agent.learners[0].active[:, 3:] = False
    choice = agent.plan()
    assert choice.status == "run"
    assert choice.local_phase == 1
    assert choice.ordered == 0
    assert choice.order_up_to == 4


def test_shift_trimming_and_replay_snapshot_agree():
    agent = learner()
    for _ in range(3):
        execute(agent)
    base = agent.learners[0]
    trace = base.traces[-1]
    base.active[0, 3:] = False
    updated, event = agent._trim(1, trace)
    assert event.kind == "trim"
    assert not base.active[:, 3:].any()
    assert base.active.any(axis=1).all()
    assert any(isinstance(e, ShiftTrim) for e in updated.events)
    q, active = updated.snapshot(len(updated.events))
    np.testing.assert_equal(active, base.active)
    np.testing.assert_equal(q, base.q)


@pytest.mark.parametrize("last_arm", [False, True])
def test_empty_trim_retires_copy_or_explicitly_preserves_the_last_copy(last_arm):
    agent = learner()
    for _ in range(3):
        execute(agent)
    if last_arm:
        agent.alive[:] = [True, False, False]
    base = agent.learners[0]
    base.active[0, 2:] = False
    base.active[1] = False
    base.active[1, 4:] = True
    trace, event = agent._trim(1, base.traces[-1])
    assert event.kind == ("safeguard" if last_arm else "retire")
    assert agent.alive[0] == last_arm
    assert base.active.any(axis=1).all()
    assert agent.safeguard_count == int(last_arm)
    np.testing.assert_equal(trace.snapshot(len(trace.events))[1], base.active)


def test_bandit_uses_completed_round_counts_and_never_eliminates_the_best():
    agent = learner()
    for _ in range(11):
        execute(agent)
    review = agent.bandit_reviews[0]
    assert review.day == 11
    assert review.phase == 0
    for assessment in review.assessments:
        assert assessment.episodes == 1
        assert assessment.threshold == pytest.approx(4 * sqrt(3**7 * log(36)))
    agent.bandit_c2 = .001
    for base, value in zip(agent.learners, [0, 2, 1]):
        base.q[0] = value
    review = agent._review_bandit(11)
    assert review.best_arm == 2
    assert agent.alive == [False, True, False]
    assert review.assessments[1].gap == 0


def test_plan_and_saved_event_replay_are_read_only():
    agent = learner()
    for _ in range(5):
        execute(agent)
    before = copy.deepcopy(agent)
    for _ in range(10):
        agent.plan()
        agent.states()
        for step in agent.steps:
            for event in step.events:
                assert event.title and event.explanation
    assert agent.steps == before.steps
    assert agent.days_observed == before.days_observed
    for first, second in zip(agent.learners, before.learners):
        np.testing.assert_equal(first.q, second.q)
        np.testing.assert_equal(first.active, second.active)


def test_horizon_does_not_count_an_incomplete_shifted_episode():
    agent = learner(total_days=9)
    for _ in range(9):
        execute(agent)
    assert [len(base.traces) for base in agent.learners] == [1, 1, 0]
    assert len(agent.learners[2].buffer) == 1
    assert agent.bandit_reviews == []
    with pytest.raises(ValueError):
        agent.plan()


def test_same_daily_draw_and_all_switch_costs_are_included(monkeypatch):
    calls = []
    def demand(config, day):
        calls.append(day)
        return 1
    monkeypatch.setattr("experiment.sample_demand", demand)
    run = PairedRun(Config(discard_at_cycle_end=False, cycles=4, capacity=5, initial_inventory=2))
    with pytest.raises(ValueError):
        run.step(1)
    assert calls == []
    for _ in range(12):
        run.step(max(run.inventory, 3))
    assert calls == list(range(1, 13))
    assert all(r.discarded == 0 for r in run.human + run.hql_history)
    assert all(a.demand == b.demand for a, b in zip(run.human, run.hql_history))
    assert len(run.comparison_rows(True)) == 12
    rows = run.comparison_rows(True)
    for row in rows:
        assert row["Bạn · tổng chi phí"] - row["Meta-HQL · tổng chi phí"] == pytest.approx(row["Chênh lệch chi phí Bạn − Meta-HQL"])
    wait = rows[3]
    assert wait["Trạng thái Meta-HQL"] == "wait_phase"
    assert wait["Meta-HQL · chi phí ngày"] == run.hql_history[3].total_cost


def test_hidden_excess_demand_and_manual_orders_cannot_change_meta_learning(monkeypatch):
    config = Config(discard_at_cycle_end=False, initial_inventory=0, cycles=12)
    monkeypatch.setattr("experiment.sample_demand", lambda cfg, day: 100)
    first = PairedRun(config, .001, .001)
    for _ in range(36):
        first.step(0)
    monkeypatch.setattr("experiment.sample_demand", lambda cfg, day: 200)
    second = PairedRun(config, .001, .001)
    for _ in range(36):
        second.step(20)
    assert first.choices == second.choices
    assert first.agent.steps == second.agent.steps
    assert first.agent.bandit_reviews == second.agent.bandit_reviews
    for a, b in zip(first.agent.learners, second.agent.learners):
        np.testing.assert_equal(a.q, b.q)
        np.testing.assert_equal(a.active, b.active)
    assert first.hql_history[-1].total_cost != second.hql_history[-1].total_cost


def test_long_aggressive_run_keeps_valid_sets_and_never_discards_inventory():
    run = PairedRun(Config(discard_at_cycle_end=False, cycles=50), .001, .001)
    for _ in range(150):
        run.step(max(run.inventory, 5))
    assert any(run.agent.alive)
    assert run.agent.bandit_reviews
    for base in run.agent.learners:
        assert np.isfinite(base.q).all()
        assert base.active.any(axis=1).all()
        for phase in range(1, 3):
            assert np.flatnonzero(base.active[phase])[-1] <= np.flatnonzero(base.active[0])[-1]
    assert all(row.discarded == 0 for row in run.hql_history)


@pytest.mark.parametrize("c2", [0, -1, float("nan")])
def test_invalid_bandit_constants_are_rejected(c2):
    with pytest.raises(ValueError):
        learner(bandit_c2=c2)
