"""
APIエンドポイントの統合テスト
"""

import pytest
from pathlib import Path
from services.token_service import TokenService, DATABASE_TOKEN_FILE, BACKEND_TOKEN_FILE

def test_health_endpoint(client):
    """ヘルスチェックエンドポイントが正常に動作することを確認."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "OK"

def test_get_password_without_auth(client):
    """認証なしでのパスワード取得が拒否されることを確認."""
    response = client.get("/secrets/database/password")
    assert response.status_code == 401

def test_get_password_with_invalid_token(client):
    """無効なトークンでのパスワード取得が拒否されることを確認."""
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/secrets/database/password", headers=headers)
    assert response.status_code == 403

def test_get_password_success(client, app):
    """有効なトークンでのパスワード取得とトークンの消費を確認."""
    with app.app_context():
        # トークンを生成
        TokenService.generate_tokens()
        
        # 生成されたトークンを取得
        token = DATABASE_TOKEN_FILE.read_text().strip()
        
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/secrets/database/password", headers=headers)
        
        assert response.status_code == 200
        assert "password" in response.get_json()
        
        # トークンが削除されたことを確認
        assert not DATABASE_TOKEN_FILE.exists()
