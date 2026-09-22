import json
import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
PARENT_ENV = BASE_DIR.parent / ".env"
CONFIG_PATH = BASE_DIR / "config.json"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
if PARENT_ENV.exists():
    load_dotenv(PARENT_ENV)

DEFAULT_CONFIG: dict[str, Any] = {
    "pipeline": {
        "jurisdiction": "",
        "topic": "",
        "step_section": "ESG Legislative Landscape",
        "limit": 0,
        "base_url": "https://step.mykajabi.com/free-digital-content",
    },
    "schedule": {
        "enabled": False,
        "frequency": "weekly",
        "hour": 2,
        "minute": 0,
        "day_of_week": "mon",
    },
    "ai": {
        "provider": "mock",
        "anthropic_api_key": "",
        "openai_api_key": "",
        "gemini_api_key": "",
        "openai_model": "gpt-4o-mini",
        "gemini_model": "gemini-flash-latest",
        "confidence_threshold": 0.8,
    },
}


def _load_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
    else:
        cfg = {}
    merged = _deep_merge(DEFAULT_CONFIG.copy(), cfg)
    return merged


def _deep_merge(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


class AppConfig:
    def __init__(self) -> None:
        self._config = _load_config()
        self._apply_env_overrides()

    def _apply_env_overrides(self) -> None:
        ai = self._config.setdefault("ai", {})
        ai["anthropic_api_key"] = os.getenv("ANTHROPIC_API_KEY", ai.get("anthropic_api_key", ""))
        ai["openai_api_key"] = os.getenv("OPENAI_API_KEY", ai.get("openai_api_key", ""))
        ai["gemini_api_key"] = os.getenv("GEMINI_API_KEY", ai.get("gemini_api_key", ""))
        ai["agentrouter_api_key"] = os.getenv("AGENTROUTER_API_KEY", ai.get("agentrouter_api_key", ""))
        if os.getenv("STEP_AI_PROVIDER"):
            ai["provider"] = os.getenv("STEP_AI_PROVIDER")

    def save(self, updated: dict[str, Any]) -> None:
        self._config = _deep_merge(self._config, updated)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2)

    @property
    def pipeline(self) -> dict[str, Any]:
        return self._config.setdefault("pipeline", {})

    @property
    def schedule(self) -> dict[str, Any]:
        return self._config.setdefault("schedule", {})

    @property
    def ai(self) -> dict[str, Any]:
        return self._config.setdefault("ai", {})

    def to_dict(self) -> dict[str, Any]:
        return dict(self._config)


config = AppConfig()
