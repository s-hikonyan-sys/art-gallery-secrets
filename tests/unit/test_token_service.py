import pytest
from services.token_service import TokenService, DATABASE_TOKEN_FILE, BACKEND_TOKEN_FILE

@pytest.mark.unit
class TestTokenService:
    def test_token_lifecycle(self, app):
        """トークンの生成、検証、消費のサイクルを一括でテスト."""
        with app.app_context():
            # 1. 生成
            TokenService.generate_tokens()
            assert DATABASE_TOKEN_FILE.exists()
            assert BACKEND_TOKEN_FILE.exists()
            
            db_token = DATABASE_TOKEN_FILE.read_text().strip()
            
            # 2. ステータス確認
            assert TokenService.get_token_status(db_token) is True
            assert DATABASE_TOKEN_FILE.exists() # まだ消えない
            
            # 3. 消費
            assert TokenService.verify_and_consume_token(db_token) is True
            assert not DATABASE_TOKEN_FILE.exists() # 消えた
            
            # 4. 全消費確認
            assert TokenService.check_all_tokens_consumed() is False
            backend_token = BACKEND_TOKEN_FILE.read_text().strip()
            TokenService.verify_and_consume_token(backend_token)
            assert TokenService.check_all_tokens_consumed() is True
