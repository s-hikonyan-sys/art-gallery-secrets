import secrets as py_secrets
from pathlib import Path
import os
from flask import current_app

TOKEN_DIR = Path(os.environ.get("TOKEN_DIR", "/app/tokens"))
DATABASE_TOKEN_FILE = TOKEN_DIR / "database_token.txt"
BACKEND_TOKEN_FILE = TOKEN_DIR / "backend_token.txt"

class TokenService:
    @staticmethod
    def generate_tokens():
        """起動時にワンタイムトークンを生成しファイルに保存する."""
        TOKEN_DIR.mkdir(parents=True, exist_ok=True)
        
        for token_file in [DATABASE_TOKEN_FILE, BACKEND_TOKEN_FILE]:
            token = py_secrets.token_urlsafe(32)
            token_file.write_text(token)
            token_file.chmod(0o600)
            current_app.logger.info(f"Generated token file: {token_file.name}")

    @staticmethod
    def verify_and_consume_token(provided_token: str) -> bool:
        """トークンを検証し、正しければファイルを削除してTrueを返す."""
        for token_file in [DATABASE_TOKEN_FILE, BACKEND_TOKEN_FILE]:
            if token_file.exists():
                stored_token = token_file.read_text().strip()
                if py_secrets.compare_digest(stored_token, provided_token):
                    token_file.unlink()
                    current_app.logger.info(f"Consumed and deleted token file: {token_file.name}")
                    return True
        return False

    @staticmethod
    def get_token_status(token_value: str) -> bool:
        """トークンが有効かどうかを確認（消費はしない）."""
        for token_file in [DATABASE_TOKEN_FILE, BACKEND_TOKEN_FILE]:
            if token_file.exists():
                stored_token = token_file.read_text().strip()
                if py_secrets.compare_digest(stored_token, token_value):
                    return True
        return False

    @staticmethod
    def check_all_tokens_consumed() -> bool:
        """全てのトークンファイルが削除されたか確認する."""
        return not DATABASE_TOKEN_FILE.exists() and not BACKEND_TOKEN_FILE.exists()

