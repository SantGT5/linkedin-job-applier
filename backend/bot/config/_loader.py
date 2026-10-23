import json
import os
from typing import Any

from app.settings_schema import SECRET_ENV, defaults


def load(section: str) -> dict[str, Any]:
    """Settings of one section: snapshot values over schema defaults."""
    values = defaults()[section]
    path = os.environ.get("APPLIER_CONFIG_FILE")
    if path:
        with open(path, encoding="utf-8") as file:
            values.update(json.load(file).get(section, {}))
    return values


def load_secrets() -> dict[str, str]:
    """Secrets come only from the environment (`.env`), never from the snapshot."""
    return {name: os.environ.get(env_var, "") for name, env_var in SECRET_ENV.items()}


def data_dir() -> str:
    return os.environ.get("DATA_DIR", "/data").rstrip("/")
