from pathlib import Path

import numpy as np
from streamlit.testing.v1 import AppTest


APP = str(Path(__file__).resolve().parents[1] / "app.py")


def app():
    instance = AppTest.from_file(APP, default_timeout=30)
    instance.query_params["model"] = "fql"
    instance.run()
    assert not instance.exception
    return instance


def test_daily_flow_q_learning_and_read_only_replay():
    instance = app()
    agent = instance.session_state.fql_run.agent
    assert agent.plan().order == (0, 0)
    for day in range(1, 4):
        instance.button(key="fql_advance").click().run()
        assert not instance.exception
        assert agent.days_observed == day
        assert len(agent.traces) == (day // 3)
    run = instance.session_state.fql_run
    before = [q.copy() for q in agent.q]
    instance.button(key="fql_q_next").click().run()
    assert instance.session_state.fql_q_cursor == 1
    instance.button(key="fql_q_finish").click().run()
    assert instance.button(key="fql_q_next").disabled
    instance.button(key="fql_q_previous").click().run()
    instance.selectbox(key="fql_decision_day").select(1).run()
    instance.selectbox(key="fql_inspect_state_1_2_0").select(-3).run()
    assert not instance.exception
    assert len(run.human) == agent.days_observed == 3
    for q, old in zip(agent.q, before):
        np.testing.assert_equal(q, old)


def test_settings_apply_and_replay_keep_the_same_demands_without_touching_another_model():
    instance = app()
    instance.number_input(key="fql_cfg_cycles").set_value(1)
    instance.button(key="FormSubmitter:fql_settings-Áp dụng và bắt đầu lại FQL").click().run()
    for _ in range(3):
        instance.button(key="fql_advance").click().run()
    assert not instance.exception
    assert instance.button(key="fql_advance").disabled
    demands = [d.flow.demand for d in instance.session_state.fql_run.human]
    instance.button(key="fql_replay").click().run()
    assert not instance.exception
    assert len(instance.session_state.fql_run.human) == 0
    for _ in range(3):
        instance.button(key="fql_advance").click().run()
    assert [d.flow.demand for d in instance.session_state.fql_run.human] == demands


def test_fql_route_preserves_an_existing_hql_game_and_returning_preserves_fql():
    instance = AppTest.from_file(APP, default_timeout=30).run()
    instance.button(key="advance_day").click().run()
    scalar = instance.session_state.experiment
    human = list(scalar.human)
    instance.query_params["model"] = "fql"
    instance.run()
    instance.button(key="fql_advance").click().run()
    assert not instance.exception
    assert instance.session_state.experiment is scalar
    assert scalar.human == human
    instance.query_params["model"] = "hql"
    instance.run()
    assert not instance.exception
    assert instance.session_state.history == human
    instance.query_params["model"] = "fql"
    instance.run()
    assert len(instance.session_state.fql_run.human) == 1


def test_comparison_uses_full_observable_costs_and_terminal_ledger():
    instance = app()
    for _ in range(3):
        instance.button(key="fql_advance").click().run()
    table = next(df.value for df in instance.dataframe if "Chênh lệch Bạn − FQL" in df.value.columns)
    run = instance.session_state.fql_run
    assert table["Nhu cầu A"].tolist() == [d.flow.demand[0] for d in run.human]
    assert table["Bạn · chi phí ngày"].sum() == sum(d.flow.total_cost for d in run.human)
    instance.radio(key="fql_history_policy").set_value("FQL").run()
    assert not instance.exception
    terminal = next(df.value for df in instance.dataframe if "Đang về cuối" in df.value.columns)
    assert terminal["Đang về cuối"].tolist() == list(run.algorithm[-1].flow.order)
