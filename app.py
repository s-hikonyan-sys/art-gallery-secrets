import logging
import os
import secrets
import string
from pathlib import Path
from http import HTTPStatus
from typing import Any, Optional
from flask import Flask, jsonify, request, Response

# configモジュールを相対パスでインポート（リポジトリルートに移動したため）
from config import Config

# --- 設定 ---
# トークンが格納されるディレクトリ（docker-composeでrwマウントされている）
TOKENS_DIR = Path("/app/tokens")
TOKENS_DIR.mkdir(parents=True, exist_ok=True)

BACKEND_TOKEN_FILE = TOKENS_DIR / "backend_token.txt"
DATABASE_TOKEN_FILE = TOKENS_DIR / "database_token.txt"

# ログ出力先
LOG_DIR = Path("/app/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# --- ロギング設定 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "secrets_api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- カスタム例外の定義 ---
class APIError(Exception):
    """APIの基本例外クラス"""
    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code

    def to_dict(self) -> dict[str, str]:
        return {"error": self.message}

class UnauthorizedError(APIError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, HTTPStatus.UNAUTHORIZED)

class ServiceMisconfiguredError(APIError):
    def __init__(self, message: str = "Service Misconfigured") -> None:
        super().__init__(message, HTTPStatus.INTERNAL_SERVER_ERROR)

class PasswordNotFoundError(APIError):
    def __init__(self, message: str = "Password Not Found") -> None:
        super().__init__(message, HTTPStatus.NOT_FOUND)

# エラーハンドラ
@app.errorhandler(APIError)
def handle_api_error(error: APIError) -> tuple[Response, int]:
    logger.error(f"API Error: {error.message} (Status: {error.status_code})")
    return jsonify(error.to_dict()), error.status_code

# --- トークン管理ヘルパー ---
def generate_random_token(length: int = 64) -> str:
    """安全なランダムトークンを生成する."""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def generate_runtime_tokens() -> None:
    """起動時に各クライアント用のワンタイムトークンを生成してファイルに書き込む."""
    try:
        # Backend用トークン
        backend_token = generate_random_token()
        BACKEND_TOKEN_FILE.write_text(backend_token, encoding="utf-8")
        BACKEND_TOKEN_FILE.chmod(0o600)
        logger.info(f"Generated backend token at {BACKEND_TOKEN_FILE}")

        # Database用トークン
        db_token = generate_random_token()
        DATABASE_TOKEN_FILE.write_text(db_token, encoding="utf-8")
        DATABASE_TOKEN_FILE.chmod(0o600)
        logger.info(f"Generated database token at {DATABASE_TOKEN_FILE}")

    except Exception as e:
        logger.critical(f"Failed to generate runtime tokens: {e}")
        raise RuntimeError(f"Token generation failed: {e}")

def get_valid_tokens() -> list[str]:
    """現在有効な全てのトークンを取得する."""
    tokens = []
    for token_file in [BACKEND_TOKEN_FILE, DATABASE_TOKEN_FILE]:
        if token_file.exists():
            try:
                tokens.append(token_file.read_text(encoding="utf-8").strip())
            except Exception as e:
                logger.error(f"Failed to read token file {token_file}: {e}")
    return tokens

def delete_token_by_value(token_value: str) -> None:
    """指定された値を持つトークンファイルを削除する."""
    for token_file in [BACKEND_TOKEN_FILE, DATABASE_TOKEN_FILE]:
        if token_file.exists():
            try:
                content = token_file.read_text(encoding="utf-8").strip()
                if content == token_value:
                    os.remove(token_file)
                    logger.info(f"Used token file deleted: {token_file}")
                    return
            except Exception as e:
                logger.error(f"Failed to process/delete token file {token_file}: {e}")

# --- リクエスト前処理 ---
@app.before_request
def verify_request_source() -> Optional[tuple[Response, int]]:
    # ヘルスチェックは認証不要
    if request.path == '/health':
        return None

    # 1. リクエストヘッダーからトークンを取得
    auth_token = request.headers.get('X-Auth-Token')
    if not auth_token:
        logger.warning(f"Missing X-Auth-Token header from: {request.remote_addr}")
        return jsonify({"error": "Missing authentication token"}), HTTPStatus.UNAUTHORIZED

    # 2. 期待される有効なトークンリストを取得
    valid_tokens = get_valid_tokens()
    if not valid_tokens:
        logger.error("No valid tokens available in the system")
        return jsonify({"error": "Service authentication is not ready"}), HTTPStatus.SERVICE_UNAVAILABLE

    # 3. 検証
    if auth_token not in valid_tokens:
        logger.warning(f"Invalid auth token attempt from: {request.remote_addr}")
        return jsonify({"error": "Invalid authentication token"}), HTTPStatus.UNAUTHORIZED
    
    return None

# --- ルートハンドラー ---
@app.route('/secrets/database/password', methods=['GET'])
def get_database_password() -> tuple[Response, int]:
    logger.info(f"Database password requested by: {request.remote_addr}")
    
    # 認証に使用されたトークンを取得
    auth_token = request.headers.get('X-Auth-Token')

    try:
        # Configから復号済みのDBパスワードを取得
        db_password = Config.DB_PASSWORD
        if not db_password:
            raise PasswordNotFoundError("Database password is not set or empty")
            
        response = jsonify({"password": db_password})
        
        # 成功レスポンスを返した後、使用済みトークンを削除
        # Flaskの after_this_request はレスポンス送信後に実行されるため安全
        @app.after_this_request
        def cleanup(response: Response) -> Response:
            if response.status_code == HTTPStatus.OK:
                delete_token_by_value(auth_token)
            return response

        return response, HTTPStatus.OK

    except APIError:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during password retrieval: {e}")
        raise APIError("An internal server error occurred", HTTPStatus.INTERNAL_SERVER_ERROR)

@app.route('/health', methods=['GET'])
def health_check() -> tuple[Response, int]:
    return jsonify({"status": "healthy"}), HTTPStatus.OK

if __name__ == '__main__':
    # サーバー起動前にトークンを生成
    generate_runtime_tokens()
    logger.info("Starting Secrets API Service...")
    app.run(host='0.0.0.0', port=5000)
