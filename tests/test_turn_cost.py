import pytest


def compute_turn_cost(state):
    previous_total = state['session_log'][-1]['total_cost'] if state['session_log'] else 0
    return state['total_session_cost'] - previous_total


def test_turn_cost_first_turn():
    state = {
        'session_log': [],
        'total_session_cost': 1.0
    }
    assert compute_turn_cost(state) == 1.0
    state['session_log'].append({'turn': 1, 'total_cost': state['total_session_cost']})


def test_turn_cost_subsequent_turns():
    state = {
        'session_log': [
            {'turn': 1, 'total_cost': 1.2},
            {'turn': 2, 'total_cost': 2.5}
        ],
        'total_session_cost': 3.0
    }
    assert compute_turn_cost(state) == pytest.approx(0.5)

