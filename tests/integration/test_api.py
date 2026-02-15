import pytest
from unittest.mock import patch
from http import HTTPStatus
from pathlib import Path
import os

# Flaskアプリケーションとカスタム例外をインポート
from app import app, BACKEND_TOKEN_FILE, APIError, UnauthorizedError, ServiceMisconfiguredError, PasswordNotFoundError
from config import Config

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_auth_token_file(tmp_path):
    # テスト用に一時的なauth_tokenファイルを作成
    auth_file = tmp_path / "auth_token.txt"
    auth_file.write_text("test_auth_token")
    with patch('app.BACKEND_TOKEN_FILE', auth_file):
        yield auth_file

@pytest.fixture
def setup_config_for_decryption(tmp_path):
    # secrets-apiが依存するConfigクラスの設定をモック
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # config/__init__.py が参照するパスを設定
    mock_config_path = config_dir / "config.yaml"
    mock_secrets_path = config_dir / "secrets.yaml.encrypted"
    mock_auth_token_path = config_dir / "auth_token.txt"

    mock_config_path.write_text("secret_key: 'test_secret_key'")
    mock_secrets_path.write_text("database:\n  password: 'encrypted:test_encrypted_password'")
    mock_auth_token_path.write_text("test_auth_token")

    with (
        patch('config.CONFIG_FILE', mock_config_path),
        patch('config.SECRETS_FILE', mock_secrets_path),
        patch('app.BACKEND_TOKEN_FILE', mock_auth_token_path),
        patch('config.secrets.SecretManager') as MockSecretManager
    ):
        # SecretManager.decryptの戻り値をモック
        mock_instance = MockSecretManager.return_value
        mock_instance.decrypt.return_value = "decrypted_test_password"

        # Config._config の初期化を強制
        Config.load_app_config()
        yield

# --- テストケース ---

def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == HTTPStatus.OK
    assert response.json == {"status": "healthy"}

def test_get_database_password_unauthorized(client):
    # トークンなし
    response = client.get('/secrets/database/password')
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert "error" in response.json

def test_get_database_password_invalid_token(client, mock_auth_token_file):
    # 不正なトークン
    response = client.get('/secrets/database/password', headers={'X-Auth-Token': 'wrong_token'})
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert "error" in response.json

def test_get_database_password_success(client, mock_auth_token_file, setup_config_for_decryption):
    # 正しいトークンと設定で成功
    response = client.get('/secrets/database/password', headers={'X-Auth-Token': 'test_auth_token'})
    assert response.status_code == HTTPStatus.OK
    assert response.json == {"password": "decrypted_test_password"}

    # トークンファイルが削除されたことを確認
    assert not mock_auth_token_file.exists()

def test_get_database_password_file_read_error(client, mock_auth_token_file, setup_config_for_decryption):
    # auth_token.txtの読み込みに失敗するケースをモック
    with patch('app.main.BACKEND_TOKEN_FILE.read_text', side_effect=IOError("Permission denied")):
        response = client.get('/secrets/database/password', headers={'X-Auth-Token': 'test_auth_token'})
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert "error" in response.json

def test_get_database_password_empty_token_file(client, mock_auth_token_file, setup_config_for_decryption):
    # auth_token.txtが空のケースをモック
    mock_auth_token_file.write_text("")
    response = client.get('/secrets/database/password', headers={'X-Auth-Token': 'test_auth_token'})
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "error" in response.json

def test_get_database_password_decryption_error(client, mock_auth_token_file):
    # Config._load_config()内で復号エラーが発生するケースをモック
    with patch('config._load_config', side_effect=Exception("Decryption failed")):
        response = client.get('/secrets/database/password', headers={'X-Auth-Token': 'test_auth_token'})
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert "error" in response.json

def test_get_database_password_not_found(client, mock_auth_token_file):
    # Config.DB_PASSWORDが空のケースをモック
    with patch.object(Config, 'DB_PASSWORD', ""):
        response = client.get('/secrets/database/password', headers={'X-Auth-Token': 'test_auth_token'})
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert "error" in response.json

def test_generate_runtime_tokens(tmp_path):
    # TOKENS_DIR をテスト用の一時ディレクトリに差し替えてテスト
    mock_tokens_dir = tmp_path / "tokens"
    mock_tokens_dir.mkdir()
    mock_backend_token_file = mock_tokens_dir / "backend_token.txt"
    mock_database_token_file = mock_tokens_dir / "database_token.txt"

    with (
        patch('app.BACKEND_TOKEN_FILE', mock_backend_token_file),
        patch('app.DATABASE_TOKEN_FILE', mock_database_token_file)
    ):
        from app import generate_runtime_tokens
        generate_runtime_tokens()

        assert mock_backend_token_file.exists()
        assert mock_database_token_file.exists()
        assert len(mock_backend_token_file.read_text()) == 64
        assert len(mock_database_token_file.read_text()) == 64
