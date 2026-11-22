from pathlib import Path

import numpy as np
from streamlit.testing.v1 import AppTest


APP = str(Path(__file__).resolve().parents[1] / "app.py")


def app():
    instance = AppTest.from_file(APP, default_timeout=30).run()
    assert not instance.exception
    return instance


def test_invalid_decision_blocks_step_and_reruns_do_not_sample_demand():
    instance = app()
    instance.number_input(key="target_stock").set_value(2).run()
    assert instance.button(key="advance_day").disabled
    assert len(instance.session_state.history) == 0
    instance.toggle(key="researcher_view").set_value(True).run()
    assert len(instance.session_state.history) == 0
    instance.number_input(key="target_stock").set_value(5).run()
    assert not instance.button(key="advance_day").disabled
    instance.button(key="advance_day").click().run()
    assert not instance.exception
    assert len(instance.session_state.history) == 1
    assert instance.session_state.history[0].ordered == 2


def test_role_toggle_filters_displayed_history_and_replay_restores_same_demand():
    instance = app()
    instance.button(key="advance_day").click().run()
    first = instance.session_state.history[0]
    observed = instance.dataframe[0].value
    assert "Nhu cầu thật D" not in observed.columns
    assert "Tổng chi phí thật" not in observed.columns
    instance.toggle(key="researcher_view").set_value(True).run()
    assert instance.dataframe[0].value["Nhu cầu thật D"].iloc[0] == first.demand
    assert len(instance.session_state.history) == 1
    instance.toggle(key="researcher_view").set_value(False).run()
    assert "Nhu cầu thật D" not in instance.dataframe[0].value.columns
    instance.button(key="replay").click().run()
    assert len(instance.session_state.history) == 0
    assert instance.session_state.inventory == 3
    instance.button(key="advance_day").click().run()
    assert instance.session_state.history[0].demand == first.demand
    assert not instance.exception


def test_cycle_reset_and_horizon_are_visible_in_app():
    instance = app()
    instance.number_input(key="cfg_cycles").set_value(1)
    instance.number_input(key="cfg_mean_0").set_value(0.0)
    instance.number_input(key="cfg_mean_1").set_value(0.0)
    instance.number_input(key="cfg_mean_2").set_value(0.0)
    instance.button(key="FormSubmitter:settings_form-Áp dụng và bắt đầu lại").click().run()
    for day in range(1, 4):
        instance.button(key="advance_day").click().run()
        assert not instance.exception
        assert len(instance.session_state.history) == day
    assert instance.session_state.inventory == 0
    assert instance.session_state.history[-1].discarded == 5
    assert instance.button(key="advance_day").disabled
    assert instance.session_state.history[-1].holding_cost == 5


def test_settings_only_apply_on_submit_and_validate_as_a_group():
    instance = app()
    instance.button(key="advance_day").click().run()
    instance.number_input(key="cfg_initial").set_value(25)
    instance.number_input(key="cfg_capacity").set_value(10)
    instance.button(key="FormSubmitter:settings_form-Áp dụng và bắt đầu lại").click().run()
    assert not instance.exception
    assert len(instance.session_state.history) == 1
    assert instance.session_state.config.capacity == 20
    assert any("Tồn kho ban đầu" in error.value for error in instance.error)
    instance.number_input(key="cfg_initial").set_value(2)
    instance.selectbox(key="cfg_mode").select("Giữ sang chu kỳ sau (nondiscarding)")
    instance.button(key="FormSubmitter:settings_form-Áp dụng và bắt đầu lại").click().run()
    assert not instance.exception
    assert len(instance.session_state.history) == 0
    assert instance.session_state.inventory == 2
    assert instance.session_state.config.capacity == 10
    assert not instance.session_state.config.discard_at_cycle_end


def test_hql_learns_only_after_day_three_and_q_replay_is_read_only():
    instance = app()
    for day in range(1, 4):
        instance.button(key="advance_day").click().run()
        assert not instance.exception
        run = instance.session_state.experiment
        assert len(run.hql_history) == day
        assert run.hql_history[-1].demand == run.human[-1].demand
        if day < 3:
            np.testing.assert_equal(run.agent.q, 3)
    original_q = run.agent.q.copy()
    assert not np.all(original_q == 3)
    instance.button(key="q_next").click().run()
    assert not instance.exception
    assert instance.session_state.q_cursor == 1
    assert len(instance.session_state.history) == 3
    np.testing.assert_equal(instance.session_state.experiment.agent.q, original_q)
    instance.button(key="q_finish").click().run()
    assert instance.session_state.q_cursor == len(run.agent.traces[0].events)
    assert instance.button(key="q_next").disabled
    instance.button(key="q_previous").click().run()
    assert not instance.exception
    assert len(instance.session_state.experiment.agent.traces) == 1
    instance.button(key="replay").click().run()
    assert not instance.exception
    np.testing.assert_equal(instance.session_state.experiment.agent.q, 3)
    assert instance.session_state.experiment.agent.traces == []


def test_comparison_reveals_true_costs_only_in_researcher_view():
    instance = app()
    instance.button(key="advance_day").click().run()
    comparison = next(df.value for df in instance.dataframe if "Chênh lệch chi phí Bạn − HQL" in df.value.columns)
    assert "Nhu cầu chung D" not in comparison.columns
    assert "Bạn · tổng chi phí" not in comparison.columns
    instance.toggle(key="researcher_view").set_value(True).run()
    comparison = next(df.value for df in instance.dataframe if "Chênh lệch chi phí Bạn − HQL" in df.value.columns)
    run = instance.session_state.experiment
    assert comparison["Nhu cầu chung D"].iloc[0] == run.human[0].demand
    assert comparison["Bạn · tổng chi phí"].iloc[0] == run.human[0].total_cost
    assert comparison["HQL · tổng chi phí"].iloc[0] == run.hql_history[0].total_cost
    assert len(run.human) == len(run.hql_history) == 1


def test_fast_confidence_variant_is_explicit_and_resets_both_policies():
    instance = app()
    instance.button(key="advance_day").click().run()
    instance.selectbox(key="cfg_confidence").select("Minh họa thu hẹp nhanh · hệ số 0.001")
    instance.button(key="FormSubmitter:settings_form-Áp dụng và bắt đầu lại").click().run()
    assert not instance.exception
    assert instance.session_state.history == []
    assert instance.session_state.experiment.hql_history == []
    assert instance.session_state.experiment.agent.confidence_scale == .001
    assert any("không mang đảm bảo lý thuyết" in warning.value for warning in instance.warning)
    for _ in range(6):
        instance.button(key="advance_day").click().run()
        assert not instance.exception
    assert not instance.session_state.experiment.agent.active.all()
    assert instance.session_state.q_episode_select == 2
    assert instance.session_state.q_cursor == 0
    # Select a past episode then continue: the next full cycle opens its own replay.
    instance.selectbox(key="q_episode_select").select(1).run()
    instance.button(key="q_next").click().run()
    assert instance.session_state.q_cursor == 1
    for _ in range(3):
        instance.button(key="advance_day").click().run()
        assert not instance.exception
    assert instance.session_state.q_episode_select == 3
    assert instance.session_state.q_cursor == 0
    assert len(instance.session_state.history) == 9
    assert instance.button(key="advance_day").disabled


def test_new_feature_migrates_existing_manual_history_without_losing_choices():
    from model import Config, sample_demand, simulate_day
    config = Config()
    previous = simulate_day(config, 1, 3, 5, sample_demand(config, 1))
    instance = AppTest.from_file(APP, default_timeout=30)
    instance.session_state["config"] = config
    instance.session_state["history"] = [previous]
    instance.session_state["inventory"] = previous.next_opening
    instance.session_state["target_stock"] = 5
    instance.run()
    assert not instance.exception
    assert instance.session_state.history == [previous]
    assert instance.session_state.experiment.hql_history[0].demand == previous.demand
    assert instance.session_state.experiment.agent.days_observed == 1
