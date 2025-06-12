import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import main


def calculate_turn_cost(state):
    previous_total = state['session_log'][-1]['total_cost'] if state['session_log'] else 0
    return state['total_session_cost'] - previous_total

def test_turn_cost_multiple_turns():
    state = {'session_log': [], 'total_session_cost': 0.5}
    assert calculate_turn_cost(state) == 0.5

    state['session_log'].append({'total_cost': 0.5})
    state['total_session_cost'] = 0.75
    assert calculate_turn_cost(state) == 0.25

    state['session_log'].append({'total_cost': 0.75})
    state['total_session_cost'] = 1.25
    assert calculate_turn_cost(state) == 0.5
