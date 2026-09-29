"""Asistente `trendscope setup`: escribe .env sin romperlo y guía cada credencial."""

from unittest.mock import patch

import pytest

from trendscope import setup_wizard as sw

AUTH = "a" * 40
CT0 = "b" * 64


def scripted(answers):
    """Prompt.ask / Confirm.ask falsos que responden en orden."""
    it = iter(answers)

    def ask(*args, **kwargs):
        try:
            v = next(it)
        except StopIteration:  # pragma: no cover — el test pidió menos respuestas
            raise AssertionError(f"pregunta inesperada: {args[0] if args else kwargs}")
        if v is None:  # Enter → valor por defecto
            return kwargs.get("default")
        return v

    return ask


def run_wizard(tmp_path, sections, prompts, confirms, models=None):
    env = tmp_path / ".env"
    wiz = sw.Wizard(env, "es", tmp_path / ".env.example")
    with patch.object(sw.Prompt, "ask", side_effect=scripted(prompts)), \
         patch.object(sw.Confirm, "ask", side_effect=scripted(confirms)), \
         patch.object(sw.Wizard, "fetch_models", return_value=models or []):
        wiz.run(sections)
        wiz.save()
    return env, wiz


def test_write_env_keeps_comments_and_order(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comentario\nGEO_TARGET=CO\nOTRA=1\n", encoding="utf-8")
    bak = sw.write_env(env, {"GEO_TARGET": "MX", "NUEVA": "con espacio"})
    text = env.read_text(encoding="utf-8")
    assert text.startswith("# comentario\nGEO_TARGET=MX\nOTRA=1\n")
    assert 'NUEVA="con espacio"' in text
    assert bak and bak.read_text(encoding="utf-8").startswith("# comentario\nGEO_TARGET=CO")
    assert sw.read_env(env)["NUEVA"] == "con espacio"


def test_write_env_starts_from_template(tmp_path):
    tpl = tmp_path / ".env.example"
    tpl.write_text("# plantilla\nOPENAI_API_KEY=\nGEO_TARGET=CO\n", encoding="utf-8")
    env = tmp_path / ".env"
    assert sw.write_env(env, {"OPENAI_API_KEY": "sk-1"}, tpl) is None
    assert env.read_text(encoding="utf-8") == "# plantilla\nOPENAI_API_KEY=sk-1\nGEO_TARGET=CO\n"


def test_ai_section_saves_provider_key_and_model_from_list(tmp_path):
    # proveedor 1 = openai; key; modelo #2 de la lista; sí usar IA para emociones
    env, _ = run_wizard(tmp_path, ["ai"], ["1", "sk-test", "2"], [True], models=["gpt-a", "gpt-b"])
    vals = sw.read_env(env)
    assert vals["LLM_PROVIDER"] == vals["NARRATOR_PROVIDER"] == "openai"
    assert vals["OPENAI_API_KEY"] == "sk-test" and vals["OPENAI_MODEL"] == "gpt-b"
    assert vals["SENTIMENT_ENGINE"] == "llm"


def test_ai_section_manual_model_and_keeps_existing_key(tmp_path):
    (tmp_path / ".env").write_text("DEEPSEEK_API_KEY=old-key\n", encoding="utf-8")
    from trendscope.llm.providers import PROVIDERS

    idx = str(list(PROVIDERS).index("deepseek") + 1)
    env, _ = run_wizard(tmp_path, ["ai"], [idx, "", "deepseek-x"], [False])
    vals = sw.read_env(env)
    assert vals["DEEPSEEK_API_KEY"] == "old-key"  # Enter no borra la key
    assert vals["DEEPSEEK_MODEL"] == "deepseek-x" and vals["LLM_PROVIDER"] == "deepseek"


def test_long_model_list_can_be_filtered(tmp_path):
    models = [f"vendor/model-{i}" for i in range(100)] + ["deepseek/deepseek-chat:free"]
    env, _ = run_wizard(tmp_path, ["ai"], ["5", "or-key", "free", "1"], [False], models=models)
    assert sw.read_env(env)["OPENROUTER_MODEL"] == "deepseek/deepseek-chat:free"


def test_ai_none_disables_llm(tmp_path):
    env, _ = run_wizard(tmp_path, ["ai"], ["0"], [])
    assert sw.read_env(env)["LLM_PROVIDER"] == "none"


def test_x_section_saves_cookies_and_rejects_garbage(tmp_path):
    env, _ = run_wizard(tmp_path, ["x"], [AUTH, CT0], [True])
    vals = sw.read_env(env)
    assert vals["TWITTER_AUTH_TOKEN"] == AUTH and vals["TWITTER_CT0"] == CT0

    # pegar algo que no es una cookie y decir que no → no se guarda
    sub = tmp_path / "sub"
    sub.mkdir()
    _, wiz = run_wizard(sub, ["x"], ["auth_token=zzz", CT0], [True, False])
    assert "TWITTER_AUTH_TOKEN" not in wiz.updates and wiz.updates["TWITTER_CT0"] == CT0


def test_reddit_section_optional(tmp_path):
    env, wiz = run_wizard(tmp_path, ["reddit"], [], [False])
    assert wiz.updates == {} and not env.exists()
    env, _ = run_wizard(tmp_path, ["reddit"], ["cookie123", "cid", "sec"], [True, True])
    vals = sw.read_env(env)
    assert vals["REDDIT_SESSION_COOKIE"] == "cookie123"
    assert vals["REDDIT_CLIENT_ID"] == "cid" and vals["REDDIT_CLIENT_SECRET"] == "sec"


def test_general_section_validates_days(tmp_path):
    env, _ = run_wizard(tmp_path, ["general"], ["mx", "99", "3"], [])
    vals = sw.read_env(env)
    assert vals["GEO_TARGET"] == "MX" and vals["MAX_AGE_DAYS"] == "3"


def test_status_never_prints_secrets(tmp_path, capsys):
    env = tmp_path / ".env"
    env.write_text(f"LLM_PROVIDER=openai\nOPENAI_API_KEY=sk-secret-123\nTWITTER_AUTH_TOKEN={AUTH}\n"
                   f"TWITTER_CT0={CT0}\n", encoding="utf-8")
    with patch.object(sw, "console", sw.Console(force_terminal=False, width=120)):
        sw.status(env, "en")
    out = capsys.readouterr().out
    assert "sk-secret" not in out and AUTH not in out
    assert "OpenAI" in out


def test_cli_rejects_unknown_section(tmp_path):
    with pytest.raises(SystemExit):
        sw.main(["nope", "--env-file", str(tmp_path / ".env")])


def test_trendscope_setup_dispatch(tmp_path):
    from trendscope import main as cli

    with patch("sys.argv", ["trendscope", "setup", "--status", "--env-file", str(tmp_path / ".env")]):
        with pytest.raises(SystemExit) as exc:
            cli.main()
    assert exc.value.code == 0


def test_reddit_cookie_from_env_file_reaches_reddit_actions(monkeypatch):
    import sys
    import types

    monkeypatch.setitem(sys.modules, "reddit_actions", types.ModuleType("reddit_actions"))
    monkeypatch.delenv("REDDIT_SESSION_COOKIE", raising=False)
    from trendscope.scrapers import reddit_comments

    with patch("trendscope.settings.settings.reddit_session_cookie", "abc"):
        assert reddit_comments._reddit_actions() is not None
    import os

    assert os.environ.get("REDDIT_SESSION_COOKIE") == "abc"
    monkeypatch.delenv("REDDIT_SESSION_COOKIE", raising=False)
