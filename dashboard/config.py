"""
config.py — centralised environment & key management
=====================================================
All API keys are loaded here from .env (never hardcoded).
Import `cfg` anywhere in the project:

    from config import cfg
    key = cfg.whale_alert_key   # None if not set → graceful fallback
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Load .env from the same directory as this file
_env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=_env_path)


@dataclass(frozen=True)
class AppConfig:
    whale_alert_key:   Optional[str] = field(default=None)
    cryptopanic_key:   Optional[str] = field(default=None)
    anthropic_key:     Optional[str] = field(default=None)

    @property
    def whale_alert_active(self) -> bool:
        return bool(self.whale_alert_key)

    @property
    def cryptopanic_active(self) -> bool:
        return bool(self.cryptopanic_key)

    @property
    def claude_active(self) -> bool:
        return bool(self.anthropic_key)

    def status_lines(self) -> list[str]:
        """Return human-readable status lines for each data source."""
        return [
            f"{'✅' if self.whale_alert_active  else '⚠️ '} Whale Alert   — "
            f"{'live' if self.whale_alert_active  else 'NO KEY — set WHALE_ALERT_API_KEY in .env (whale-alert.io)'}",
            f"{'✅' if self.cryptopanic_active  else '⚠️ '} CryptoPanic   — "
            f"{'live' if self.cryptopanic_active  else 'NO KEY — set CRYPTOPANIC_API_KEY in .env (cryptopanic.com/developers/api)'}",
            f"{'✅' if self.claude_active        else '⚠️ '} Claude/Anthropic — "
            f"{'live (headline AI)' if self.claude_active else 'NO KEY — set ANTHROPIC_API_KEY in .env — falling back to keyword classifier'}",
        ]


def _load() -> AppConfig:
    """Read env vars, strip whitespace and placeholder values."""

    def _get(var: str) -> Optional[str]:
        val = os.getenv(var, "").strip()
        if not val or val.startswith("your_") or val == "":
            return None
        return val

    cfg = AppConfig(
        whale_alert_key = _get("WHALE_ALERT_API_KEY"),
        cryptopanic_key = _get("CRYPTOPANIC_API_KEY"),
        anthropic_key   = _get("ANTHROPIC_API_KEY"),
    )

    # Print status once at import time (visible in terminal / Streamlit logs)
    all_ok = all([cfg.whale_alert_active, cfg.cryptopanic_active, cfg.claude_active])
    if not all_ok:
        print("\n── Applore Trading POC · API Key Status ──────────────────────")
        for line in cfg.status_lines():
            print(" ", line)
        print("  Copy dashboard/.env.example → dashboard/.env and fill in keys.")
        print("───────────────────────────────────────────────────────────────\n")

    return cfg


# Module-level singleton — import this everywhere
cfg: AppConfig = _load()
