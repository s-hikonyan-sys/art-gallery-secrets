"""pytest設定ファイル
プロジェクト全体のテストで共通利用するフィクスチャを定義します。
"""

import pytest
import os
import shutil
from pathlib import Path

# テスト用のディレクトリ設定
TEST_TOKEN_DIR = Path("/tmp/art-gallery-secrets-tests/tokens")
TEST_LOG_DIR = Path("/tmp/art-gallery-secrets-tests/logs")
TEST_CONFIG_DIR = Path("/tmp/art-gallery-secrets-tests/config")

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """テスト環境のセットアップ."""
    # ディレクトリ作成
    TEST_TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    TEST_LOG_DIR.mkdir(parents=True, exist_ok=True)
    TEST_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    # 環境変数の設定 (TokenServiceなどが参照するパスを差し替えるのは難しいため、
    # 実際にはコンテナ内での動作を想定したパスになっていますが、
    # ユニットテストではモックを使用します)
    
    yield
    
    # 後片付け
    if TEST_TOKEN_DIR.parent.exists():
        shutil.rmtree(TEST_TOKEN_DIR.parent)

@pytest.fixture
def app():
    """テスト用Flaskアプリケーションインスタンスを作成."""
    # FLASK_ENVをtestingに設定して、起動時のトークン生成などを制御できるようにする
    os.environ["FLASK_ENV"] = "testing"
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    return app

@pytest.fixture
def client(app):
    """テストクライアントインスタンスを作成."""
    return app.test_client()
