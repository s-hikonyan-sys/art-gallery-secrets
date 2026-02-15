import os
from pathlib import Path
from typing import Any, Optional

import yaml

from .secrets import SecretManager

# 設定ファイルのパス
CONFIG_DIR = Path("/app/config")
CONFIG_FILE = CONFIG_DIR / "config.yaml"
SECRETS_FILE = CONFIG_DIR / "secrets.yaml.encrypted"


def _get_secrets_from_encrypted_file(secret_key: str) -> dict:
    """Fernetで暗号化されたファイルから機密情報を取得."""
    if not SECRETS_FILE.exists():
        return {}

    try:
        with open(SECRETS_FILE, "r", encoding="utf-8") as f:
            secrets_data = yaml.safe_load(f) or {}

        if not secrets_data:
            return {}

        secret_manager = SecretManager(secret_key=secret_key)
        decrypted_secrets = {}

        for key, value in secrets_data.items():
            if isinstance(value, dict):
                decrypted_secrets[key] = {}
                for sub_key, sub_value in value.items():
                    if SecretManager.is_encrypted(str(sub_value)):
                        encrypted_value = SecretManager.extract_encrypted_value(str(sub_value))
                        decrypted_secrets[key][sub_key] = secret_manager.decrypt(encrypted_value)
                    else:
                        decrypted_secrets[key][sub_key] = sub_value
            elif SecretManager.is_encrypted(str(value)):
                encrypted_value = SecretManager.extract_encrypted_value(str(value))
                decrypted_secrets[key] = secret_manager.decrypt(encrypted_value)
            else:
                decrypted_secrets[key] = value

        return decrypted_secrets
    except Exception as e:
        print(f"Error loading encrypted secrets: {e}")
        return {}


def _load_config() -> dict:
    """設定をロードする."""
    config = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Error loading config.yaml: {e}")

    secret_key = config.get("secret_key")
    if secret_key:
        secrets = _get_secrets_from_encrypted_file(secret_key)
        # データベース設定をマージ
        if "database" in secrets:
            if "database" not in config:
                config["database"] = {}
            config["database"].update(secrets["database"])

    return config


class Config:
    """アプリケーション設定クラス."""

    _config = _load_config()

    # サーバー設定
    PORT = int(os.environ.get("PORT", 5000))
    DEBUG = os.environ.get("FLASK_ENV") == "development"

    # データベースパスワード (復号化済み)
    DB_PASSWORD = _config.get("database", {}).get("password")

    @classmethod
    def load_app_config(cls) -> None:
        """設定を再読み込みする."""
        cls._config = _load_config()
        cls.DB_PASSWORD = cls._config.get("database", {}).get("password")
