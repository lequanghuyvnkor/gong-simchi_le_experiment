from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from model import Config, history_rows, sample_demand, simulate_day


def test_inventory_and_cost_identities_across_feasible_states():
    for discard in (True, False):
        config = Config(capacity=6, initial_inventory=0, discard_at_cycle_end=discard)
        for day in (1, 3, 4):
            for opening in range(7):
                for target in range(opening, 7):
                    for demand in range(10):
                        result = simulate_day(config, day, opening, target, demand)
                        assert result.opening + result.ordered == result.sales + result.remaining
                        assert result.sales + result.lost == demand
                        assert result.remaining == result.next_opening + result.discarded
                        assert result.total_cost - result.pseudo_cost == config.penalty_rate * demand
                        assert result.holding_cost == config.holding_rate * result.remaining
                        assert result.next_opening >= 0
                        assert result.discarded == (result.remaining if discard and day == 3 else 0)


@pytest.mark.parametrize("demand", [5, 9])
def test_selling_exactly_stock_censors_demand_even_when_no_actual_loss(demand):
    result = simulate_day(Config(), 1, 3, 5, demand)
    assert result.censored
    observed = history_rows([result])[0]
    assert observed["Quan sát nhu cầu"] == "D ≥ 5"
    assert "Nhu cầu thật D" not in observed
    assert "Nhu cầu mất L" not in observed
    assert "Chi phí mất doanh số" not in observed
    assert "Tổng chi phí thật" not in observed
    assert history_rows([result], researcher=True)[0]["Nhu cầu thật D"] == demand


def test_zero_stock_does_not_reveal_zero_demand():
    result = simulate_day(Config(initial_inventory=0), 1, 0, 0, 0)
    assert result.censored
    assert history_rows([result])[0]["Quan sát nhu cầu"] == "D ≥ 0"


def test_unsold_stock_reveals_demand_and_no_lost_sales():
    result = simulate_day(Config(), 1, 3, 8, 2)
    assert not result.censored
    assert result.lost == 0
    assert history_rows([result])[0]["Quan sát nhu cầu"] == "D = 2"


def test_cycle_reset_happens_after_holding_cost():
    config = Config(holding_rate=2, penalty_rate=4)
    result = simulate_day(config, 3, 3, 10, 2)
    assert result.remaining == 8
    assert result.holding_cost == 16
    assert result.discarded == 8
    assert result.next_opening == 0
    carried = simulate_day(Config(discard_at_cycle_end=False), 3, 3, 10, 2)
    assert carried.discarded == 0
    assert carried.next_opening == 8


@pytest.mark.parametrize("opening,target,demand", [(3, 2, 5), (3, 21, 5), (-1, 5, 3), (1, 4, -1), (1, 4.5, 2)])
def test_invalid_decisions_and_inputs_are_rejected(opening, target, demand):
    with pytest.raises(ValueError):
        simulate_day(Config(), 1, opening, target, demand)


def test_replay_demand_is_deterministic_and_respects_three_day_phases():
    config = Config(demand_means=(0, 8, 0), cycles=5)
    path = [sample_demand(config, day) for day in range(1, config.total_days + 1)]
    assert path == [sample_demand(config, day) for day in range(1, config.total_days + 1)]
    assert all(demand == 0 for index, demand in enumerate(path) if index % 3 != 1)
    # Different inventory decisions never enter the demand generator.
    alternative = Config(demand_means=config.demand_means, cycles=5, initial_inventory=0, capacity=50)
    assert path == [sample_demand(alternative, day) for day in range(1, config.total_days + 1)]
    assert len(set(path[1::3])) > 1


@pytest.mark.parametrize("kwargs", [{"initial_inventory":21}, {"holding_rate":0}, {"penalty_rate":float("nan")}, {"cycles":0}, {"demand_means":(1,2)}, {"demand_means":(1,-1,2)}])
def test_invalid_config_is_rejected(kwargs):
    with pytest.raises(ValueError):
        Config(**kwargs)


def test_horizon_is_enforced():
    with pytest.raises(ValueError):
        sample_demand(Config(cycles=1), 4)
    with pytest.raises(ValueError):
        simulate_day(Config(cycles=1), 4, 0, 5, 4)
