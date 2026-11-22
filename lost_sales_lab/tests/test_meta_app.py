import copy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from streamlit.testing.v1 import AppTest

from meta_hql import MetaHQL
from model import Config, sample_demand, simulate_day


APP = str(Path(__file__).resolve().parents[1] / "app.py")


def app():
    instance = AppTest.from_file(APP, default_timeout=30).run()
    instance.selectbox(key="cfg_mode").select("Giữ sang chu kỳ sau (nondiscarding)")
    instance.number_input(key="cfg_cycles").set_value(12)
    instance.number_input(key="cfg_initial").set_value(2)
    instance.number_input(key="cfg_capacity").set_value(5)
    for phase in range(3):
        instance.number_input(key=f"cfg_mean_{phase}").set_value(0.0)
    instance.button(key="FormSubmitter:settings_form-Áp dụng và bắt đầu lại").click().run()
    assert not instance.exception
    return instance


def test_meta_keeps_stock_and_waits_without_learning_or_resetting_at_calendar_cycle():
    instance = app()
    for _ in range(4):
        instance.button(key="advance_day").click().run()
        assert not instance.exception
    run = instance.session_state.experiment
    assert isinstance(run.agent, MetaHQL)
    assert all(r.discarded == 0 for r in run.human + run.hql_history)
    assert instance.session_state.inventory == 5
    assert run.hql_history[3].opening == run.hql_history[2].remaining == 5
    assert run.choices[3].status == "wait_phase"
    assert run.choices[3].ordered == 0
    assert [len(base.traces) for base in run.agent.learners] == [1, 0, 0]


def test_bandit_event_buttons_and_copy_selection_do_not_advance_days_or_retrain():
    instance = app()
    for _ in range(3):
        instance.button(key="advance_day").click().run()
    agent = instance.session_state.experiment.agent
    before = copy.deepcopy(agent)
    instance.button(key="meta_next").click().run()
    assert instance.session_state.meta_cursor == 2
    instance.button(key="meta_finish").click().run()
    assert instance.button(key="meta_next").disabled
    instance.button(key="meta_previous").click().run()
    instance.selectbox(key="meta_q_arm").select(2).run()
    instance.selectbox(key="meta_day_select").select(1).run()
    assert not instance.exception
    assert instance.session_state.meta_cursor == 1
    assert agent.steps == before.steps
    assert len(instance.session_state.history) == agent.days_observed == 3
    for first, second in zip(agent.learners, before.learners):
        np.testing.assert_equal(first.q, second.q)
        np.testing.assert_equal(first.active, second.active)


def test_full_bandit_phase_review_is_inspectable_and_past_days_stay_read_only():
    instance = app()
    for _ in range(11):
        instance.button(key="advance_day").click().run()
        assert not instance.exception
    agent = instance.session_state.experiment.agent
    assert agent.bandit_phase == 1
    assert [len(base.traces) for base in agent.learners] == [1, 1, 1]
    review_step = agent.steps[-1]
    event_number = next(index + 1 for index, event in enumerate(review_step.events) if event.kind == "bandit_review")
    instance.slider(key="meta_cursor").set_value(event_number).run()
    assert not instance.exception
    table = next(df.value for df in instance.dataframe if "Ngưỡng 2CB₂" in df.value.columns)
    assert table["K_w"].tolist() == [1, 1, 1]
    instance.selectbox(key="meta_day_select").select(4).run()
    instance.button(key="meta_next").click().run()
    assert any("Chờ điều kiện chuyển" in item.value for item in instance.markdown)
    assert len(instance.session_state.history) == 11


def test_meta_comparison_respects_view_and_includes_wait_day_costs():
    instance = app()
    for _ in range(4):
        instance.button(key="advance_day").click().run()
    table = next(df.value for df in instance.dataframe if "Chênh lệch chi phí Bạn − Meta-HQL" in df.value.columns)
    assert "Nhu cầu chung D" not in table
    assert "Meta-HQL · tổng chi phí" not in table
    assert table["Trạng thái Meta-HQL"].tolist()[-1] == "wait_phase"
    instance.toggle(key="researcher_view").set_value(True).run()
    assert not instance.exception
    table = next(df.value for df in instance.dataframe if "Chênh lệch chi phí Bạn − Meta-HQL" in df.value.columns)
    run = instance.session_state.experiment
    assert table["Meta-HQL · tổng chi phí"].iloc[-1] == sum(r.total_cost for r in run.hql_history)
    assert table["Meta-HQL · chi phí ngày"].iloc[3] == 5
    assert len(table) == len(run.human) == 4


def test_bandit_demo_setting_is_labeled_and_replay_resets_all_copies():
    instance = app()
    instance.selectbox(key="cfg_bandit").select("Minh họa thu hẹp nhanh · C₂ = 0.001")
    instance.button(key="FormSubmitter:settings_form-Áp dụng và bắt đầu lại").click().run()
    for _ in range(3):
        instance.button(key="advance_day").click().run()
    assert not instance.exception
    assert instance.session_state.experiment.agent.bandit_c2 == .001
    assert "minh họa" in instance.session_state.experiment.agent.label
    instance.button(key="replay").click().run()
    assert not instance.exception
    agent = instance.session_state.experiment.agent
    assert agent.days_observed == 0
    assert agent.steps == []
    assert agent.inventory == 2
    assert agent.bandit_c2 == .001
    for base in agent.learners:
        np.testing.assert_equal(base.q, 3)


def test_existing_manual_nondiscarding_session_is_migrated_without_loss():
    config = Config(discard_at_cycle_end=False)
    previous = simulate_day(config, 1, 3, 5, sample_demand(config, 1))
    instance = AppTest.from_file(APP, default_timeout=30)
    instance.session_state["config"] = config
    instance.session_state["history"] = [previous]
    instance.session_state["inventory"] = previous.next_opening
    instance.session_state["target_stock"] = 5
    instance.session_state["experiment"] = SimpleNamespace(version=2)
    instance.run()
    assert not instance.exception
    assert instance.session_state.history == [previous]
    agent = instance.session_state.experiment.agent
    assert isinstance(agent, MetaHQL)
    assert agent.days_observed == 1
    assert instance.session_state.experiment.hql_history[0].demand == previous.demand


def test_meta_link_opens_ready_to_play_without_overriding_an_existing_run():
    instance = AppTest.from_file(APP, default_timeout=30)
    instance.query_params["model"] = "meta"
    instance.run()
    assert not instance.exception
    assert not instance.session_state.config.discard_at_cycle_end
    assert instance.session_state.config.cycles == 12
    assert isinstance(instance.session_state.experiment.agent, MetaHQL)
    instance.query_params["model"] = "hql"
    instance.run()
    assert not instance.session_state.config.discard_at_cycle_end
