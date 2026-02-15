import pytest
import os
import shutil
from pathlib import Path
from unittest.mock import patch

# テスト対象モジュールのインポート
import config
from config import Config, _load_config
from config.secrets import SecretManager

# テスト用の一時ディレクトリパス
TEST_CONFIG_BASE_DIR = Path("/tmp/test_config_secrets")
TEST_CONFIG_DIR = TEST_CONFIG_BASE_DIR / "config"
TEST_SECRETS_FILE = TEST_CONFIG_DIR / "secrets.yaml.encrypted"
TEST_CONFIG_FILE = TEST_CONFIG_DIR / "config.yaml"

@pytest.fixture(autouse=True)
def setup_teardown_config_env():
    """各テスト実行前に一時ディレクトリを作成し、後に削除する."""
    TEST_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    # configモジュールレベルの定数を一時的に差し替える
    with patch("config.CONFIG_FILE", TEST_CONFIG_FILE), \
         patch("config.SECRETS_FILE", TEST_SECRETS_FILE):
        yield
        
    if TEST_CONFIG_BASE_DIR.exists():
        shutil.rmtree(TEST_CONFIG_BASE_DIR)

def create_dummy_config_files(secret_key="test_secret_key", db_password="test_db_password", encrypted=True):
    """ダミーのconfig.yamlとsecrets.yaml.encryptedを作成."""
    # config.yaml
    config_content = f"secret_key: {secret_key}\n"
    TEST_CONFIG_FILE.write_text(config_content)

    # secrets.yaml.encrypted
    if encrypted:
        sm = SecretManager(secret_key=secret_key)
        encrypted_pw = sm.encrypt(db_password)
        # Note: encrypt returns a base64 string, but it's already encoded as base64 by Fernet. 
        # The SecretManager.encrypt in this project does: base64.urlsafe_b64encode(encrypted).decode()
        secrets_content = f"database:\n  password: \"encrypted:{encrypted_pw}\"\n"
    else:
        secrets_content = f"database:\n  password: \"{db_password}\"\n"
    TEST_SECRETS_FILE.write_text(secrets_content)

@pytest.mark.unit
class TestConfig:
    def test_load_config_success_encrypted(self):
        """設定が正しくロードされ、パスワードが復号されることを確認."""
        create_dummy_config_files()
        Config.load_app_config()
        assert Config.DB_PASSWORD == "test_db_password"

    def test_load_config_success_plaintext(self):
        """設定が正しくロードされ、平文パスワードが取得されることを確認."""
        create_dummy_config_files(encrypted=False)
        Config.load_app_config()
        assert Config.DB_PASSWORD == "test_db_password"

    def test_load_config_no_config_file(self):
        """config.yamlがない場合に、DB_PASSWORDがNoneになることを確認."""
        if TEST_CONFIG_FILE.exists():
            TEST_CONFIG_FILE.unlink()
        Config.load_app_config()
        assert Config.DB_PASSWORD is None

    def test_load_config_no_secrets_file(self):
        """secrets.yaml.encryptedがない場合に、DB_PASSWORDがNoneになることを確認."""
        TEST_CONFIG_FILE.write_text("secret_key: test_secret_key\n")
        if TEST_SECRETS_FILE.exists():
            TEST_SECRETS_FILE.unlink()
        Config.load_app_config()
        assert Config.DB_PASSWORD is None
