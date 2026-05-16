"""Small helpers for checking and setting pyngrok auth tokens."""

from __future__ import annotations

import os
from pathlib import Path

from pyngrok import conf, ngrok


def _candidate_config_paths() -> tuple[Path, ...]:
    home = Path(os.path.expanduser("~"))
    return (
        home / ".ngrok2" / "ngrok.yml",
        home / "Library" / "Application Support" / "ngrok" / "ngrok.yml",
        home / ".config" / "ngrok" / "ngrok.yml",
    )


def has_ngrok_auth_token() -> bool:
    """Return whether pyngrok/ngrok appears to have an auth token configured."""
    if conf.get_default().auth_token:
        return True

    for path in _candidate_config_paths():
        if not path.exists():
            continue
        try:
            if "authtoken" in path.read_text():
                return True
        except OSError:
            continue

    return False


def set_ngrok_auth_token(token: str) -> bool:
    """Persist an ngrok auth token through pyngrok."""
    normalized = token.strip()
    if not normalized:
        return False
    ngrok.set_auth_token(normalized)
    return True
