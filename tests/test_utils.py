import os
import json
import asyncio
import sys
import pathlib
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from ai_council.utils import load_config, generate_filename_slug, write_audit_log


class DummyClient:
    """Minimal async client to emulate openai.AsyncOpenAI"""

    class _Completions:
        async def create(self, model, messages, temperature, max_tokens):
            class Response:
                choices = [type('obj', (), {
                    'message': type('msg', (), {'content': 'Simple Slug Title'})
                })]
            return Response()

    def __init__(self):
        self.chat = type('chat', (), {'completions': self._Completions()})()


def test_load_config(tmp_path):
    file = tmp_path / "config.toml"
    file.write_text("[section]\nkey='value'\n", encoding="utf-8")
    cfg = load_config(str(file))
    assert cfg["section"]["key"] == "value"


def test_load_config_missing(tmp_path):
    missing = tmp_path / "missing.toml"
    with pytest.raises(FileNotFoundError):
        load_config(str(missing))


def test_generate_filename_slug():
    client = DummyClient()
    slug = asyncio.run(
        generate_filename_slug("Prompt", client, {"m1": "model-name"}, "system")
    )
    assert slug == "simple_slug_title"


def test_generate_filename_slug_no_models():
    client = DummyClient()
    slug = asyncio.run(
        generate_filename_slug("Prompt", client, {}, "system")
    )
    assert slug == "untitled_session"


def test_write_audit_log(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_audit_log(1, {"a": 1})
    p = tmp_path / "logs" / "turn_001_log.json"
    assert p.exists()
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == {"a": 1}
