from dataclasses import replace
from types import SimpleNamespace
from app.config import config, runtime_scope
from app.database import Store


def test_auto_final_answer_uses_visible_budget_and_preserves_explicit_thinking(tmp_path, monkeypatch):
    import app.agent as agent

    sent = []

    def create(**arguments):
        sent.append(arguments)
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
        thinking="auto",
    )
    for mode in ["auto", "high"]:
        with runtime_scope(replace(selected, thinking=mode)):
            agent.completion(
                Store(tmp_path / (mode + ".sqlite3")),
                [{"role": "user", "content": "Return final JSON"}],
                final_answer=True,
            )
    assert sent[0]["extra_body"]["thinking"]["type"] == "disabled"
    assert sent[1]["extra_body"]["thinking"]["type"] == "enabled"
    assert all(r["max_tokens"] == 1800 for r in sent)
