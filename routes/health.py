"""ヘルスチェックルート.

アプリケーションの動作確認用エンドポイントを提供します。"""

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
@health_bp.route("/api/health", methods=["GET"])
def health():
    """ヘルスチェックエンドポイント.

    Returns:
        JSON形式のステータス情報"""
    return jsonify({"status": "OK", "message": "Secrets API is running"})
