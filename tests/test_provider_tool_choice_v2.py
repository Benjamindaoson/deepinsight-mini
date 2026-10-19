from dataclasses import replace
from types import SimpleNamespace
from app.config import config, runtime_scope
from app.database import Store


def test_official_deepseek_does_not_receive_unsupported_required_choice(tmp_path, monkeypatch):
    import app.agent as agent

    sent = {}

    def create(**arguments):
        sent.update(arguments)
        return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5), choices=[])

    monkeypatch.setattr(
        agent,
        "OpenAI",
        lambda **kwargs: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))),
    )
    selected = replace(
        config(),
        key="SYNTHETIC",
        provider="deepseek",
        base_url="https://api.deepseek.com",
        model="deepseek-flash",
    )
    with runtime_scope(selected):
        agent.completion(
            Store(tmp_path / "db.sqlite3"),
            [{"role": "user", "content": "Check saved evidence"}],
            agent.TOOLS,
            force_tool=True,
        )
    assert sent["tool_choice"] == "auto"
