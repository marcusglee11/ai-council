import os
import pathlib
import sys
import json
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from ai_council import session


def test_end_session_writes_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    state = {
        'session_log': [
            {'turn': 1, 'user_prompt': 'Question', 'rapporteur_report': 'Answer'},
        ],
        'output_filename': 'report.md'
    }
    session.end_session(state)
    report = tmp_path / 'output' / 'report.md'
    assert report.exists()
    content = report.read_text(encoding='utf-8')
    assert 'Question' in content and 'Answer' in content
