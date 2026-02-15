"""秘密情報ルート.

パスワード復号化APIのエンドポイントを定義します。"""

from flask import Blueprint, request, jsonify, current_app
from config import Config
from services.token_service import TokenService

secrets_bp = Blueprint("secrets", __name__, url_prefix="/secrets")

@secrets_bp.before_request
def verify_authorization():
    """全ての秘密情報APIリクエストのBearerトークンを検証する."""
    if request.path == "/health" or request.path == "/api/health":
        return # ヘルスチェックは認証不要

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        current_app.logger.warning("Missing or invalid Authorization header.")
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    token = auth_header[len("Bearer "):]

    if not TokenService.get_token_status(token):
        current_app.logger.warning("Token not available or expired during pre-request check.")
        return jsonify({"error": "Token not available or expired"}), 403

@secrets_bp.route("/database/password", methods=["GET"])
def get_database_password():
    """データベースパスワードを復号して返す."""
    token = request.headers.get("Authorization")[len("Bearer "):]

    if TokenService.verify_and_consume_token(token):
        current_app.logger.info("Database password provided and token consumed.")
        return jsonify({"password": Config.DB_PASSWORD})

    current_app.logger.error("Failed to provide database password due to token issue (after pre-check).")
    return jsonify({"error": "Failed to retrieve database password"}), 500
