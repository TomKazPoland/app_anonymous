from __future__ import annotations

import os
from pathlib import Path
from dotenv import dotenv_values


def load_openai_api_key() -> str:
    """
    Priority:
    1) OPENAI_API_KEY from ENV
    2) file: ${SECRETS_DIR:-$HOME/secrets}/openai_key.python.env (dotenv format)
    """
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    secrets_dir = os.getenv("SECRETS_DIR")
    if secrets_dir and secrets_dir.strip():
        base = Path(secrets_dir).expanduser().resolve()
    else:
        base = Path.home() / "secrets"

    secret_file = base / "openai_key.python.env"
    if not secret_file.exists():
        raise FileNotFoundError(f"Secret file not found: {secret_file}")

    data = dotenv_values(str(secret_file))
    key = (data.get("OPENAI_API_KEY") or "").strip()
    if not key:
        raise ValueError(f"OPENAI_API_KEY not set in: {secret_file}")

    return key
