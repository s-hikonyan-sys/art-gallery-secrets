import pytest
import os
from app import create_app

@pytest.fixture(scope="session")
def app():
    """テスト用Flaskアプリケーションインスタンスを作成."""
    os.environ["FLASK_ENV"] = "testing" # テスト時はトークン生成をスキップさせるため環境変数をセット
    app = create_app()
    app.config["TESTING"] = True  # テストモードを有効にする
    yield app


@pytest.fixture
def client(app):
    """テストクライアントインスタンスを作成."""
    return app.test_client()
