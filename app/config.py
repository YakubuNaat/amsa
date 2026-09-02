"""
Central configuration loader for AMSA.

Reads secrets/config from environment variables (via a local .env file if present).
Never hardcode the Groq API key in source.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


@dataclass(frozen=True)
class Config:
    groq_api_key: str
    groq_model: str
    output_dir: Path
    config_dir: Path
    templates_dir: Path

    @classmethod
    def load(cls) -> "Config":
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key or api_key.startswith("gsk_your_key_here"):
            raise RuntimeError(
                "GROQ_API_KEY is not set. Create a free key at "
                "https://console.groq.com (API Keys section), then put it "
                "in a .env file at the project root as GROQ_API_KEY=gsk_..."
            )
        return cls(
            groq_api_key=api_key,
            groq_model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
            output_dir=Path(os.environ.get("AMSA_OUTPUT_DIR", str(_ROOT / "output"))),
            config_dir=_ROOT / "config",
            templates_dir=_ROOT / "templates",
        )


CONFIG = None


def get_config() -> Config:
    global CONFIG
    if CONFIG is None:
        CONFIG = Config.load()
    return CONFIG
