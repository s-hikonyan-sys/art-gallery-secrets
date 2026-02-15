import pytest
import os
import time
from unittest.mock import patch, MagicMock
from flask import Flask

# テスト対象モジュールのインポート
import app as app_module
from services.token_service import TokenService

@pytest.fixture
def mock_app():
    """アプリケーションのモック."""
    mock = MagicMock(spec=Flask)
    mock.logger = MagicMock()
    return mock

@pytest.mark.unit
class TestAppLifecycle:
    @patch('os._exit')
    @patch('time.sleep', return_value=None) # sleepをスキップ
    @patch('services.token_service.TokenService.check_all_tokens_consumed')
    def test_monitor_shutdown_all_tokens_consumed(self, mock_check_tokens, mock_sleep, mock_exit, mock_app):
        """全てのトークンが消費された場合にシャットダウンすることを確認."""
        mock_check_tokens.side_effect = [False, True]
        
        with patch('app.app', mock_app):
            # monitor_shutdownが無限ループなので、os._exitが呼ばれたら例外を投げるようにする
            mock_exit.side_effect = SystemExit
            
            with pytest.raises(SystemExit):
                app_module.monitor_shutdown()
        
        mock_exit.assert_called_once_with(0)
        mock_app.logger.info.assert_any_call("All tokens consumed. Shutting down secrets-api.")

    @patch('os._exit')
    @patch('time.sleep', return_value=None)
    @patch('services.token_service.TokenService.check_all_tokens_consumed', return_value=False)
    def test_monitor_shutdown_timeout(self, mock_check_tokens, mock_sleep, mock_exit, mock_app):
        """タイムアウトした場合にシャットダウンすることを確認."""
        mock_exit.side_effect = SystemExit
        
        # time.time() の挙動をモック
        with patch('time.time') as mock_time:
            # 初期時間、1回目のループ、2回目のループ（タイムアウト）
            mock_time.side_effect = [1000, 1000, 1301]
            
            with patch('app.app', mock_app):
                with pytest.raises(SystemExit):
                    app_module.monitor_shutdown()
        
        mock_exit.assert_called_once_with(0)
        mock_app.logger.info.assert_any_call("Token lifetime expired. Shutting down secrets-api.")
