import os
import yaml
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Dict, Any


class Settings(BaseSettings):
    tinvest_token: str = ""
    iis_account_id: str = ""
    tmon_account_id: str = ""
    bcs_refresh_token: str = ""
    finam_token: str = ""
    finam_client_id: str = ""
    alor_refresh_token: str = ""
    alor_portfolio: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    api_host: str = "0.0.0.0"
    api_port: int = 8085

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def _resolve_cfg_path(path: str = "/app/config.yaml") -> Path:
    cfg_path = Path(path)
    if not cfg_path.exists():
        cfg_path = Path(__file__).resolve().parent.parent / "config.yaml"
    return cfg_path


def load_yaml_config(path: str = "/app/config.yaml") -> Dict[str, Any]:
    cfg_path = _resolve_cfg_path(path)
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml_config(data: Dict[str, Any], path: str = "/app/config.yaml") -> None:
    cfg_path = _resolve_cfg_path(path)
    tmp_path = cfg_path.with_suffix(".yaml.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    os.replace(tmp_path, cfg_path)
