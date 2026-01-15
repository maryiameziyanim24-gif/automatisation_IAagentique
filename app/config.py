from __future__ import annotations
import os
from dataclasses import dataclass


@dataclass
class Settings:
    use_llm_default: bool = False
    openai_api_key: str | None = None
    openai_model: str = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    openai_base_url: str | None = os.environ.get("OPENAI_BASE_URL")


def get_settings() -> Settings:
    s = Settings()
    s.openai_api_key = os.environ.get("OPENAI_API_KEY")
    return s
