"""設定管理モジュール.

設定ファイル（config.yaml）から設定を読み込み、アプリケーション全体で使用する設定を提供します。
機密情報（パスワードなど）はFernetで暗号化されたファイルから取得します。"""

from pathlib import Path
from typing import Any

import yaml

# SecretManagerは同じディレクトリに配置される想定
from .secrets import SecretManager

# 設定ファイルのパス
CONFIG_DIR = Path(__file__).parent
CONFIG_FILE = CONFIG_DIR / "config.yaml"
SECRETS_FILE = CONFIG_DIR / "secrets.yaml.encrypted"


def _get_secrets_from_encrypted_file(secret_key: str) -> dict:
    """Fernetで暗号化されたファイルから機密情報を取得.

    注意: 環境変数は使用しません。コンテナ内のファイルから読み込みます。
    """
    if not SECRETS_FILE.exists():
        raise FileNotFoundError(
            f"必須ファイルが見つかりません: {SECRETS_FILE}\n"
            "Ansibleデプロイ時に配置されるファイルです。"
        )

    try:
        # secrets.yaml.encryptedを読み込む
        with open(SECRETS_FILE, "r", encoding="utf-8") as f:
            secrets_data = yaml.safe_load(f) or {}

        if not secrets_data:
            raise ValueError(f"{SECRETS_FILE} が空です")

        # SecretManagerで復号化
        secret_manager = SecretManager(secret_key=secret_key)

        # 暗号化された値を復号化
        decrypted_secrets = {}
        for key, value in secrets_data.items():
            if isinstance(value, dict):
                decrypted_secrets[key] = {}
                for sub_key, sub_value in value.items():
                    if SecretManager.is_encrypted(str(sub_value)):
                        encrypted_value = SecretManager.extract_encrypted_value(
                            str(sub_value)
                        )
                        decrypted_secrets[key][sub_key] = secret_manager.decrypt(
                            encrypted_value
                        )
                    else:
                        decrypted_secrets[key][sub_key] = sub_value
            elif SecretManager.is_encrypted(str(value)):
                encrypted_value = SecretManager.extract_encrypted_value(str(value))
                decrypted_secrets[key] = secret_manager.decrypt(encrypted_value)
            else:
                decrypted_secrets[key] = value

        return decrypted_secrets
    except (FileNotFoundError, yaml.YAMLError, PermissionError) as e:
        raise RuntimeError(f"{SECRETS_FILE} の読み込みに失敗しました: {e}") from e


def _load_config_file() -> dict:
    """設定ファイルを読み込む（必須）."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"必須ファイルが見つかりません: {CONFIG_FILE}\n"
            "config.yamlが見つかりません。Ansibleデプロイ時に自動生成されるはずです。"
        )

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
            if not config:
                raise ValueError(f"{CONFIG_FILE} が空です")
            return config
    except (FileNotFoundError, yaml.YAMLError, PermissionError) as e:
        raise RuntimeError(f"{CONFIG_FILE} の読み込みに失敗しました: {e}") from e


def _load_secrets_from_config_and_encrypted_file(config: dict) -> dict:
    """機密情報を暗号化ファイルから取得（必須）.

    secrets.yaml.encryptedはFernetで暗号化されており、config.yamlのsecret_keyで復号化します。
    """
    secret_key = config.get("secret_key", "")
    if not secret_key:
        raise ValueError("config.yamlにsecret_keyが設定されていません")

    secrets = _get_secrets_from_encrypted_file(secret_key=secret_key)
    if not secrets:
        raise ValueError("secrets.yaml.encryptedが空です")
    return secrets


def _load_all_config() -> dict:
    """すべての設定を読み込んでマージする."""
    # config.yamlを読み込む
    config = _load_config_file()

    # secrets.yaml.encryptedを読み込んで復号化
    secrets = _load_secrets_from_config_and_encrypted_file(config)

    # 機密情報をconfigにマージ
    if "database" in secrets and isinstance(secrets["database"], dict):
        if "database" not in config:
            config["database"] = {}
        if isinstance(config["database"], dict):
            config["database"].update(secrets["database"])

    # 必須項目の検証（Secrets APIサービス固有）
    required_keys = ["server", "secret_key", "database"] # secrets_api自体は参照しない
    for key in required_keys:
        if key not in config:
            raise ValueError(f"config.yamlに必須項目 '{key}' がありません")
    
    # database.passwordは必須（暗号化ファイルから取得）
    if "database" in config and "password" not in config["database"]:
        raise ValueError(
            "config.yamlにdatabase.passwordがありません（暗号化ファイルから取得される必要があります）"
        )

    return config


class Config:
    """アプリケーション設定クラス.

    設定ファイル（config.yaml, secrets.yaml.encrypted）から設定値を読み込み、型安全にアクセスできるようにします。
    """

    # 設定を読み込む
    _config = _load_all_config()

    # サーバー設定（Secrets APIサービス固有）
    PORT: int = _config["server"]["port"]
    FLASK_ENV: str = _config["server"]["flask_env"]
    DEBUG: bool = _config["server"].get("debug", False)

    # Secrets APIが使用する秘密鍵
    SECRET_KEY_FOR_API: str = _config["secret_key"]

    # データベースパスワード (復号済み)
    DB_PASSWORD: str = _config.get("database", {}).get("password", "")

    @classmethod
    def load_app_config(cls) -> None:
        """アプリケーション起動時に設定を明示的に読み込む."""
        cls._config = _load_all_config()
        cls.DB_PASSWORD = cls._config.get("database", {}).get("password", "")
