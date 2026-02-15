import os
from pathlib import Path

# テスト用のディレクトリ設定 (インポート前に環境変数を設定して、モジュールレベルの定数がこれらを使うようにする)
TEST_TOKEN_DIR = Path("/tmp/art-gallery-secrets-tests/tokens")
TEST_LOG_DIR = Path("/tmp/art-gallery-secrets-tests/logs")
TEST_CONFIG_DIR = Path("/tmp/art-gallery-secrets-tests/config")

os.environ["TOKEN_DIR"] = str(TEST_TOKEN_DIR)
os.environ["LOG_DIR"] = str(TEST_LOG_DIR)
os.environ["APP_ROOT"] = str(TEST_CONFIG_DIR.parent)
os.environ["FLASK_ENV"] = "testing"

import pytest
import shutil

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """テスト環境のセットアップ."""
    # ディレクトリ作成
    TEST_TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    TEST_LOG_DIR.mkdir(parents=True, exist_ok=True)
    TEST_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    yield
    
    # 後片付け
    if TEST_TOKEN_DIR.parent.exists():
        shutil.rmtree(TEST_TOKEN_DIR.parent)

@pytest.fixture
def app():
    """テスト用Flaskアプリケーションインスタンスを作成."""
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    return app

@pytest.fixture
def client(app):
    """テストクライアントインスタンスを作成."""
    return app.test_client()
