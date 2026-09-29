"""Asistente de configuración: `trendscope setup`.

Pregunta paso a paso (país, IA + modelo, X, Reddit), explica de dónde sacar
cada credencial y guarda todo en .env sin tocar el resto del archivo.

    trendscope setup              # todo
    trendscope setup ai           # solo la IA
    trendscope setup x reddit     # solo esas secciones
    trendscope setup --status     # qué está configurado (sin mostrar secretos)
"""

from __future__ import annotations

import argparse
import locale
import os
import re
import shutil
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()

SECTIONS = ("general", "ai", "x", "reddit")

# ── Textos (es / en) ─────────────────────────────────────────────────────────
T = {
    "es": {
        "title": "Configuración de TrendScope",
        "intro": "Te voy a preguntar lo necesario y lo guardo en [bold]{env}[/bold].\n"
                 "Todo es opcional: Enter deja el valor actual. Los secretos no se muestran al escribir.",
        "general": "País y ventana de tiempo",
        "geo": "País por defecto (código de 2 letras, ej. CO, MX, US, BR, ES)",
        "days": "Días hacia atrás que cuentan como 'reciente' (1-30)",
        "ai": "Inteligencia artificial (resumen y, si quieres, análisis de emociones)",
        "ai_pick": "¿Qué IA quieres usar? (número)",
        "ai_none": "Ninguna (solo resumen estadístico)",
        "ai_keys": "Saca tu API key aquí: [link={url}]{url}[/link]",
        "ai_key": "Pega la API key de {label}",
        "ai_keep": "(Enter = dejar la que ya tienes)",
        "ai_base": "URL base de la API (compatible con OpenAI, ej. http://localhost:1234/v1)",
        "ollama_host": "Dirección de Ollama",
        "ollama_hint": "Instala Ollama (https://ollama.com) y descarga un modelo: [bold]ollama pull <modelo>[/bold]",
        "models_loading": "Buscando los modelos disponibles…",
        "models_fail": "No pude traer la lista de modelos ({err}). Escribe el nombre a mano.",
        "models_list": "Modelos disponibles (muestro {n} de {total}):",
        "model_pick": "Modelo (número de la lista o nombre exacto)",
        "model_filter": "Hay {total} modelos. Escribe parte del nombre para filtrar (ej. gpt, claude, free) o Enter",
        "model_type": "Nombre del modelo",
        "sent_llm": "¿Usar esta IA también para leer las emociones de los comentarios? "
                    "(más precisa en cualquier idioma, pero gasta tokens)",
        "x": "X / Twitter (respuestas reales de la gente)",
        "x_why": "TrendScope lee X con tus cookies de sesión (vía xactions). No necesitas la API paga de X.",
        "x_steps": (
            "Cómo sacarlas (2 minutos):\n"
            "  1. Abre [bold]https://x.com[/bold] en Chrome/Edge/Firefox e inicia sesión.\n"
            "     Recomendado: una cuenta secundaria, no la principal.\n"
            "  2. Presiona [bold]F12[/bold] → pestaña [bold]Application[/bold] (Firefox: [bold]Storage[/bold])\n"
            "     → [bold]Cookies[/bold] → [bold]https://x.com[/bold].\n"
            "  3. Copia el valor de la cookie [bold]auth_token[/bold] y el de [bold]ct0[/bold].\n"
            "  Si cierras sesión en X las cookies dejan de servir y hay que repetir esto."
        ),
        "x_ask": "¿Configurar X ahora?",
        "x_auth": "Valor de auth_token",
        "x_ct0": "Valor de ct0",
        "x_bad": "Eso no parece una cookie {name} válida (solo letras a-f y números). ¿Guardarla igual?",
        "reddit": "Reddit (posts y comentarios)",
        "reddit_why": "Reddit funciona [bold]sin credenciales[/bold]. Solo configura esto si el doctor "
                      "muestra error 403 o quieres más volumen.",
        "reddit_ask": "¿Configurar Reddit ahora?",
        "reddit_ra": "Opcional: instala reddit-actions para mejores resultados: [bold]pip install -e \".[reddit]\"[/bold]",
        "reddit_cookie_steps": (
            "Cookie de sesión (arregla el 403):\n"
            "  1. Abre [bold]https://www.reddit.com[/bold] e inicia sesión.\n"
            "  2. [bold]F12[/bold] → [bold]Application[/bold] → [bold]Cookies[/bold] → https://www.reddit.com\n"
            "  3. Copia el valor de la cookie [bold]reddit_session[/bold]."
        ),
        "reddit_cookie": "Valor de reddit_session",
        "reddit_app_ask": "¿También quieres usar la API oficial (client id / secret)?",
        "reddit_app_steps": (
            "App de Reddit (gratis):\n"
            "  1. Entra a [bold]https://www.reddit.com/prefs/apps[/bold] → [bold]create another app[/bold].\n"
            "  2. Tipo [bold]script[/bold], redirect uri: http://localhost:8080\n"
            "  3. El client id es el código corto debajo del nombre; el secret está en 'secret'."
        ),
        "reddit_id": "Client id",
        "reddit_secret": "Client secret",
        "saved": "Guardado en [bold]{env}[/bold] ({n} valores). Copia anterior: {bak}",
        "nothing": "No cambió nada.",
        "doctor_ask": "¿Probar ahora las fuentes con el doctor?",
        "next": "Listo. Arranca con: [bold]trendscope-api[/bold] y abre http://localhost:8000/dashboard",
        "status": "Estado de la configuración ({env})",
        "yes": "sí", "no": "no",
        "st_ai": "IA por defecto", "st_model": "Modelo", "st_x": "X (cookies)",
        "st_reddit": "Reddit", "st_reddit_free": "sin credenciales (modo público)",
        "st_geo": "País", "st_days": "Días", "st_engine": "Motor de emociones",
        "cancel": "Cancelado. No se guardó nada.",
    },
    "en": {
        "title": "TrendScope setup",
        "intro": "I'll ask what's needed and save it to [bold]{env}[/bold].\n"
                 "Everything is optional: Enter keeps the current value. Secrets are hidden while typing.",
        "general": "Country and time window",
        "geo": "Default country (2-letter code, e.g. US, GB, CO, MX, BR)",
        "days": "How many days back count as 'recent' (1-30)",
        "ai": "Artificial intelligence (summary and, optionally, emotion analysis)",
        "ai_pick": "Which AI do you want to use? (number)",
        "ai_none": "None (statistical summary only)",
        "ai_keys": "Get your API key here: [link={url}]{url}[/link]",
        "ai_key": "Paste your {label} API key",
        "ai_keep": "(Enter = keep the current one)",
        "ai_base": "API base URL (OpenAI-compatible, e.g. http://localhost:1234/v1)",
        "ollama_host": "Ollama address",
        "ollama_hint": "Install Ollama (https://ollama.com) and pull a model: [bold]ollama pull <model>[/bold]",
        "models_loading": "Fetching available models…",
        "models_fail": "Couldn't fetch the model list ({err}). Type the name manually.",
        "models_list": "Available models (showing {n} of {total}):",
        "model_pick": "Model (number from the list or exact name)",
        "model_filter": "There are {total} models. Type part of a name to filter (e.g. gpt, claude, free) or Enter",
        "model_type": "Model name",
        "sent_llm": "Also use this AI to read the emotions in comments? "
                    "(more accurate in any language, but uses tokens)",
        "x": "X / Twitter (real replies from people)",
        "x_why": "TrendScope reads X with your session cookies (via xactions). You don't need X's paid API.",
        "x_steps": (
            "How to get them (2 minutes):\n"
            "  1. Open [bold]https://x.com[/bold] in Chrome/Edge/Firefox and log in.\n"
            "     Recommended: a secondary account, not your main one.\n"
            "  2. Press [bold]F12[/bold] → [bold]Application[/bold] tab (Firefox: [bold]Storage[/bold])\n"
            "     → [bold]Cookies[/bold] → [bold]https://x.com[/bold].\n"
            "  3. Copy the value of the [bold]auth_token[/bold] cookie and the [bold]ct0[/bold] cookie.\n"
            "  If you log out of X the cookies stop working and you'll need to repeat this."
        ),
        "x_ask": "Set up X now?",
        "x_auth": "auth_token value",
        "x_ct0": "ct0 value",
        "x_bad": "That doesn't look like a valid {name} cookie (only letters a-f and digits). Save it anyway?",
        "reddit": "Reddit (posts and comments)",
        "reddit_why": "Reddit works [bold]without credentials[/bold]. Only set this up if the doctor "
                      "shows a 403 error or you want more volume.",
        "reddit_ask": "Set up Reddit now?",
        "reddit_ra": "Optional: install reddit-actions for better results: [bold]pip install -e \".[reddit]\"[/bold]",
        "reddit_cookie_steps": (
            "Session cookie (fixes 403):\n"
            "  1. Open [bold]https://www.reddit.com[/bold] and log in.\n"
            "  2. [bold]F12[/bold] → [bold]Application[/bold] → [bold]Cookies[/bold] → https://www.reddit.com\n"
            "  3. Copy the value of the [bold]reddit_session[/bold] cookie."
        ),
        "reddit_cookie": "reddit_session value",
        "reddit_app_ask": "Also use the official API (client id / secret)?",
        "reddit_app_steps": (
            "Reddit app (free):\n"
            "  1. Go to [bold]https://www.reddit.com/prefs/apps[/bold] → [bold]create another app[/bold].\n"
            "  2. Type [bold]script[/bold], redirect uri: http://localhost:8080\n"
            "  3. The client id is the short code under the app name; the secret is under 'secret'."
        ),
        "reddit_id": "Client id",
        "reddit_secret": "Client secret",
        "saved": "Saved to [bold]{env}[/bold] ({n} values). Previous copy: {bak}",
        "nothing": "Nothing changed.",
        "doctor_ask": "Test the data sources now with the doctor?",
        "next": "Done. Start with: [bold]trendscope-api[/bold] and open http://localhost:8000/dashboard",
        "status": "Configuration status ({env})",
        "yes": "yes", "no": "no",
        "st_ai": "Default AI", "st_model": "Model", "st_x": "X (cookies)",
        "st_reddit": "Reddit", "st_reddit_free": "no credentials (public mode)",
        "st_geo": "Country", "st_days": "Days", "st_engine": "Emotion engine",
        "cancel": "Cancelled. Nothing was saved.",
    },
}


def detect_lang() -> str:
    raw = os.environ.get("LANG") or os.environ.get("LC_ALL") or ""
    if not raw:
        try:
            raw = locale.getlocale()[0] or ""
        except Exception:
            raw = ""
    return "es" if raw.lower().startswith("es") else "en"


# ── .env ─────────────────────────────────────────────────────────────────────
_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$")


def read_env(path: Path) -> dict[str, str]:
    """Valores del .env (sin comillas). Archivo inexistente → {}."""
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _LINE.match(line)
        if m and not line.lstrip().startswith("#"):
            out[m.group(1)] = _unquote(m.group(2).strip())
    return out


def _unquote(v: str) -> str:
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def _quote(v: str) -> str:
    return f'"{v}"' if re.search(r"[\s#;\"']", v) else v


def write_env(path: Path, updates: dict[str, str], template: Path | None = None) -> Path | None:
    """Actualiza/añade claves en .env conservando comentarios y orden.

    Si .env no existe se parte de la plantilla (.env.example). Devuelve la ruta
    de la copia de respaldo (o None si el archivo era nuevo).
    """
    backup = None
    if path.exists():
        backup = path.with_name(path.name + ".bak")
        shutil.copy2(path, backup)
        lines = path.read_text(encoding="utf-8").splitlines()
    elif template and template.exists():
        lines = template.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    pending = dict(updates)
    for i, line in enumerate(lines):
        m = _LINE.match(line)
        if m and not line.lstrip().startswith("#") and m.group(1) in pending:
            key = m.group(1)
            lines[i] = f"{key}={_quote(pending.pop(key))}"
    if pending:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("# Añadido por `trendscope setup`")
        lines.extend(f"{k}={_quote(v)}" for k, v in pending.items())

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)  # contiene secretos
    except OSError:
        pass
    return backup


def mask(v: str) -> str:
    if not v:
        return ""
    return "•" * 4 + v[-4:] if len(v) > 8 else "•" * len(v)


def looks_like_hex_cookie(v: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{20,200}", v or ""))


# ── Asistente ────────────────────────────────────────────────────────────────
class Wizard:
    def __init__(self, env_path: Path, lang: str = "es", template: Path | None = None):
        self.env_path = env_path
        self.template = template
        self.t = T.get(lang, T["en"])
        self.current = read_env(env_path)
        self.updates: dict[str, str] = {}

    # utilidades
    def val(self, key: str, default: str = "") -> str:
        return self.updates.get(key, self.current.get(key, default))

    def set(self, key: str, value: str) -> None:
        if value != self.current.get(key, None):
            self.updates[key] = value

    def ask(self, key: str, prompt: str, default: str = "") -> str:
        v = Prompt.ask(prompt, default=self.val(key, default) or None) or ""
        v = v.strip()
        self.set(key, v)
        return v

    def ask_secret(self, key: str, prompt: str) -> str:
        cur = self.val(key)
        label = f"{prompt} {self.t['ai_keep']} [dim]{mask(cur)}[/dim]" if cur else prompt
        v = (Prompt.ask(label, password=True, default="", show_default=False) or "").strip()
        if v:
            self.set(key, v)
            return v
        return cur

    def header(self, key: str) -> None:
        console.print()
        console.rule(f"[bold cyan]{self.t[key]}")

    # secciones
    def general(self) -> None:
        self.header("general")
        geo = Prompt.ask(self.t["geo"], default=self.val("GEO_TARGET", "CO")).strip().upper()[:2]
        self.set("GEO_TARGET", geo)
        while True:
            days = Prompt.ask(self.t["days"], default=self.val("MAX_AGE_DAYS", "7")).strip()
            if days.isdigit() and 1 <= int(days) <= 30:
                self.set("MAX_AGE_DAYS", days)
                break

    def ai(self) -> None:
        from trendscope.llm.providers import PROVIDERS

        self.header("ai")
        provs = list(PROVIDERS.values())
        current = self.val("LLM_PROVIDER") or self.val("NARRATOR_PROVIDER")
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_row("[cyan]0[/cyan]", self.t["ai_none"])
        for i, p in enumerate(provs, 1):
            mark = " [green]●[/green]" if p.id == current else ""
            table.add_row(f"[cyan]{i}[/cyan]", p.label + mark)
        console.print(table)
        default_idx = next((str(i) for i, p in enumerate(provs, 1) if p.id == current), "0")
        choice = Prompt.ask(self.t["ai_pick"], choices=[str(i) for i in range(len(provs) + 1)],
                            default=default_idx)
        if choice == "0":
            self.set("LLM_PROVIDER", "none")
            self.set("NARRATOR_PROVIDER", "none")
            return
        p = provs[int(choice) - 1]
        self.set("LLM_PROVIDER", p.id)
        self.set("NARRATOR_PROVIDER", p.id)
        self.set("NARRATIVE_ENABLED", "true")

        key_env = (p.key_setting or "").upper()
        if p.id == "ollama":
            console.print(self.t["ollama_hint"])
            self.ask("OLLAMA_HOST", self.t["ollama_host"], "http://localhost:11434")
            self.set("OLLAMA_ENABLED", "true")
        elif p.id == "custom":
            self.ask("LLM_BASE_URL", self.t["ai_base"])
            self.ask_secret("LLM_API_KEY", self.t["ai_key"].format(label=p.label))
        else:
            if p.keys_url:
                console.print(self.t["ai_keys"].format(url=p.keys_url))
            self.ask_secret(key_env, self.t["ai_key"].format(label=p.label))

        self.choose_model(p)

        engine = self.val("SENTIMENT_ENGINE", "local")
        use_llm = Confirm.ask(self.t["sent_llm"], default=engine == "llm")
        self.set("SENTIMENT_ENGINE", "llm" if use_llm else ("local" if engine == "llm" else engine))

    def choose_model(self, p) -> None:
        model_env = (p.model_setting or "").upper()
        if not model_env:
            return
        models = self.fetch_models(p)
        current = self.val(model_env) or p.default_model
        if len(models) > 40:
            q = (Prompt.ask(self.t["model_filter"].format(total=len(models)), default="",
                            show_default=False) or "").strip().lower()
            if q:
                models = [m for m in models if q in m.lower()] or models
        if models:
            shown = models[:40]
            console.print(self.t["models_list"].format(n=len(shown), total=len(models)))
            table = Table(show_header=False, box=None, padding=(0, 2))
            for i, m in enumerate(shown, 1):
                table.add_row(f"[cyan]{i}[/cyan]", m + (" [green]●[/green]" if m == current else ""))
            console.print(table)
            raw = Prompt.ask(self.t["model_pick"], default=current or None) or ""
            raw = raw.strip()
            if raw.isdigit() and 1 <= int(raw) <= len(shown):
                raw = shown[int(raw) - 1]
        else:
            raw = (Prompt.ask(self.t["model_type"], default=current or None) or "").strip()
        if raw:
            self.set(model_env, raw)

    def fetch_models(self, p) -> list[str]:
        """Lista de modelos usando los valores recién escritos (sin guardar aún)."""
        from trendscope.llm import client as llm_client
        from trendscope.settings import settings

        overrides = {}
        for attr in (p.key_setting, p.base_url_setting, "ollama_host", "ollama_enabled"):
            if attr and attr.upper() in self.updates:
                val = self.updates[attr.upper()]
                overrides[attr] = (val.lower() == "true") if attr == "ollama_enabled" else val
        saved = {k: getattr(settings, k, None) for k in overrides}
        console.print(f"[dim]{self.t['models_loading']}[/dim]")
        try:
            for k, v in overrides.items():
                setattr(settings, k, v)
            llm_client._MODELS_CACHE.pop(p.id, None)
            return sorted(llm_client.list_models(p.id, timeout=15))
        except Exception as e:
            console.print(f"[yellow]{self.t['models_fail'].format(err=str(e)[:160])}[/yellow]")
            return []
        finally:
            for k, v in saved.items():
                setattr(settings, k, v)

    def x(self) -> None:
        self.header("x")
        console.print(self.t["x_why"])
        if not Confirm.ask(self.t["x_ask"], default=not self.val("TWITTER_AUTH_TOKEN")):
            return
        console.print(Panel(self.t["x_steps"], border_style="dim"))
        for key, name, label in (("TWITTER_AUTH_TOKEN", "auth_token", "x_auth"),
                                 ("TWITTER_CT0", "ct0", "x_ct0")):
            before = self.val(key)
            v = self.ask_secret(key, self.t[label])
            if v and v != before and not looks_like_hex_cookie(v):
                if not Confirm.ask(self.t["x_bad"].format(name=name), default=False):
                    self.updates.pop(key, None)
                    if before != self.current.get(key, ""):
                        self.updates[key] = before

    def reddit(self) -> None:
        self.header("reddit")
        console.print(self.t["reddit_why"])
        if not Confirm.ask(self.t["reddit_ask"], default=False):
            return
        console.print(self.t["reddit_ra"])
        console.print(Panel(self.t["reddit_cookie_steps"], border_style="dim"))
        self.ask_secret("REDDIT_SESSION_COOKIE", self.t["reddit_cookie"])
        if Confirm.ask(self.t["reddit_app_ask"], default=False):
            console.print(Panel(self.t["reddit_app_steps"], border_style="dim"))
            self.ask("REDDIT_CLIENT_ID", self.t["reddit_id"])
            self.ask_secret("REDDIT_CLIENT_SECRET", self.t["reddit_secret"])

    def run(self, sections: list[str]) -> dict[str, str]:
        console.print(Panel(self.t["intro"].format(env=self.env_path), title=self.t["title"],
                            border_style="cyan"))
        for s in sections:
            getattr(self, s)()
        return self.updates

    def save(self) -> None:
        if not self.updates:
            console.print(self.t["nothing"])
            return
        bak = write_env(self.env_path, self.updates, self.template)
        console.print(f"\n[green]{self.t['saved'].format(env=self.env_path, n=len(self.updates), bak=bak or '—')}[/green]")


def status(env_path: Path, lang: str = "es") -> None:
    """Resumen de lo configurado, sin mostrar secretos."""
    t = T.get(lang, T["en"])
    env = read_env(env_path)
    prov = env.get("LLM_PROVIDER") or env.get("NARRATOR_PROVIDER") or "openrouter"
    from trendscope.llm.providers import get

    p = get(prov)
    model = env.get((p.model_setting or "").upper(), "") if p else ""
    yes, no = f"[green]{t['yes']}[/green]", f"[red]{t['no']}[/red]"
    table = Table(title=t["status"].format(env=env_path), show_header=False)
    table.add_row(t["st_geo"], env.get("GEO_TARGET", "CO"))
    table.add_row(t["st_days"], env.get("MAX_AGE_DAYS", "7"))
    key_ok = True
    if p and p.key_setting and p.id not in ("ollama",):
        key_ok = bool(env.get(p.key_setting.upper()))
    table.add_row(t["st_ai"], f"{p.label if p else prov} " + ("" if prov == "none" else (yes if key_ok else no)))
    table.add_row(t["st_model"], model or "—")
    table.add_row(t["st_engine"], env.get("SENTIMENT_ENGINE", "local"))
    x_ok = bool(env.get("TWITTER_AUTH_TOKEN") and env.get("TWITTER_CT0")) or bool(env.get("TWITTER_COOKIES"))
    table.add_row(t["st_x"], yes if x_ok else no)
    r_ok = env.get("REDDIT_SESSION_COOKIE") or env.get("REDDIT_CLIENT_ID")
    table.add_row(t["st_reddit"], yes if r_ok else t["st_reddit_free"])
    console.print(table)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trendscope setup",
                                     description="Interactive setup: AI provider/model, X, Reddit")
    parser.add_argument("sections", nargs="*",
                        help=f"Sections to configure: {', '.join(SECTIONS)} (default: all)")
    parser.add_argument("--env-file", default=".env", help="Path to the .env file (default: ./.env)")
    parser.add_argument("--lang", choices=["es", "en"], default=None, help="Wizard language")
    parser.add_argument("--status", action="store_true", help="Show what is configured and exit")
    args = parser.parse_args(argv)

    bad = [s for s in args.sections if s not in SECTIONS]
    if bad:
        parser.error(f"unknown section(s): {', '.join(bad)} — choose from {', '.join(SECTIONS)}")

    lang = args.lang or detect_lang()
    env_path = Path(args.env_file)
    template = env_path.with_name(".env.example")
    if args.status:
        status(env_path, lang)
        return 0

    wizard = Wizard(env_path, lang, template)
    try:
        wizard.run(args.sections or list(SECTIONS))
    except (KeyboardInterrupt, EOFError):
        console.print(f"\n[yellow]{wizard.t['cancel']}[/yellow]")
        return 1
    wizard.save()
    status(env_path, lang)
    try:
        if wizard.updates and Confirm.ask(wizard.t["doctor_ask"], default=False):
            from trendscope.ops import main as ops_main

            ops_main(["--doctor"])
    except (KeyboardInterrupt, EOFError):
        pass
    console.print(wizard.t["next"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
