import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import os
import secrets
import string
from http import HTTPStatus
from typing import Any, Optional
from flask import Flask, jsonify, request, Response, after_this_request

from config import Config

# --- 設定 (モジュールレベル定数として保持し、テストでパッチ可能にする) ---
TOKENS_DIR = Path("/app/tokens")
BACKEND_TOKEN_FILE = TOKENS_DIR / "backend_token.txt"
DATABASE_TOKEN_FILE = TOKENS_DIR / "database_token.txt"
LOG_DIR = Path("/app/logs")

def create_app() -> Flask:
    """
    Flaskアプリケーションのファクトリ関数 (backend/app.py に準拠).
    """
    # アプリケーション起動時にConfigクラスを明示的に初期化
    Config.load_app_config()

    app = Flask(__name__)

    # ディレクトリ作成とログ設定 (backend に準拠)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    TOKENS_DIR.mkdir(parents=True, exist_ok=True)

    # アプリケーションログ
    file_handler = RotatingFileHandler(
        LOG_DIR / "secrets_api.log", maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]")
    )
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)

    # サーバー起動前にトークンを生成 (テスト時はスキップ)
    if os.environ.get("FLASK_ENV") != "testing":
        generate_runtime_tokens()

    # --- ルートハンドラー定義 ---

    @app.route('/secrets/database/password', methods=['GET'])
    def get_database_password() -> tuple[Response, int]:
        app.logger.info(f"Database password requested by: {request.remote_addr}")
        
        auth_token = request.headers.get('X-Auth-Token')
        if not auth_token:
            return jsonify({"error": "Missing authentication token"}), HTTPStatus.UNAUTHORIZED

        valid_tokens = get_valid_tokens()
        if not valid_tokens:
            return jsonify({"error": "Service authentication is not ready"}), HTTPStatus.SERVICE_UNAVAILABLE
        if auth_token not in valid_tokens:
            return jsonify({"error": "Invalid authentication token"}), HTTPStatus.UNAUTHORIZED

        try:
            db_password = Config.DB_PASSWORD
            if not db_password:
                return jsonify({"error": "Password Not Found"}), HTTPStatus.NOT_FOUND
                
            @after_this_request
            def cleanup(response: Response) -> Response:
                if response.status_code == HTTPStatus.OK:
                    delete_token_by_value(auth_token)
                return response

            return jsonify({"password": db_password}), HTTPStatus.OK

        except Exception as e:
            app.logger.exception(f"Unexpected error: {e}")
            return jsonify({"error": "Internal server error"}), HTTPStatus.INTERNAL_SERVER_ERROR

    @app.route('/health', methods=['GET'])
    def health_check() -> tuple[Response, int]:
        return jsonify({"status": "healthy"}), HTTPStatus.OK

    return app

# --- ヘルパー関数 ---

def generate_random_token(length: int = 64) -> str:
    """安全なランダムトークンを生成する."""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def generate_runtime_tokens() -> None:
    """起動時に各クライアント用のワンタイムトークンを生成してファイルに書き込む."""
    try:
        backend_token = generate_random_token()
        BACKEND_TOKEN_FILE.write_text(backend_token, encoding="utf-8")
        BACKEND_TOKEN_FILE.chmod(0o600)
        
        db_token = generate_random_token()
        DATABASE_TOKEN_FILE.write_text(db_token, encoding="utf-8")
        DATABASE_TOKEN_FILE.chmod(0o600)
    except Exception as e:
        raise RuntimeError(f"Token generation failed: {e}")

def get_valid_tokens() -> list[str]:
    """現在有効な全てのトークンを取得する."""
    tokens = []
    for token_file in [BACKEND_TOKEN_FILE, DATABASE_TOKEN_FILE]:
        if token_file.exists():
            tokens.append(token_file.read_text(encoding="utf-8").strip())
    return tokens

def delete_token_by_value(token_value: str) -> None:
    """指定された値を持つトークンファイルを削除する."""
    for token_file in [BACKEND_TOKEN_FILE, DATABASE_TOKEN_FILE]:
        if token_file.exists():
            if token_file.read_text(encoding="utf-8").strip() == token_value:
                os.remove(token_file)
                return

# アプリケーションインスタンス
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
