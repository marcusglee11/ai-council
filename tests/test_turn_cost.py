import pytest


def compute_turn_cost(state):
    previous_total = state['session_log'][-1]['total_cost'] if state['session_log'] else 0
    return state['total_session_cost'] - previous_total


def test_first_turn_cost():
    state = {'session_log': [], 'total_session_cost': 0.5}
    assert compute_turn_cost(state) == pytest.approx(0.5)


def test_subsequent_turn_cost():
    state = {'session_log': [{'total_cost': 0.5}], 'total_session_cost': 1.1}
    assert compute_turn_cost(state) == pytest.approx(0.6)


def test_multiple_turns():
    state = {'session_log': [{'total_cost': 0.5}, {'total_cost': 1.1}], 'total_session_cost': 1.4}
    assert compute_turn_cost(state) == pytest.approx(0.3)
