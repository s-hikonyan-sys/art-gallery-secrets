import logging
import os
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask
from config import Config
from routes import secrets_bp, health_bp
from services.token_service import TokenService

def create_app() -> Flask:
    """Flaskアプリケーションのファクトリ."""
    # 設定の読み込み
    Config.load_app_config()
    
    app = Flask(__name__)

    # ブループリントの登録
    app.register_blueprint(health_bp)
    app.register_blueprint(secrets_bp)

    # ログ設定
    log_dir = Path("/app/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_dir / "secrets.log", maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
    ))
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)

    # 起動時にトークンを生成
    with app.app_context(): # アプリケーションコンテキスト内で実行
        TokenService.generate_tokens()
        app.logger.info("One-time tokens generated successfully.")

    return app

app = create_app()

def monitor_shutdown():
    """トークンの使用状況とタイムアウトを監視し、自動終了する."""
    start_time = time.time()
    timeout = 300  # 5分
    
    while True:
        # 両方のトークンが使用済み（ファイルが削除された）かチェック
        if TokenService.check_all_tokens_consumed():
            app.logger.info("All tokens consumed. Shutting down secrets-api.")
            os._exit(0)
            
        # タイムアウトチェック
        if time.time() - start_time > timeout:
            app.logger.info("Token lifetime expired. Shutting down secrets-api.")
            os._exit(0)
            
        time.sleep(5)

if __name__ == "__main__":
    # シャットダウン監視スレッドを開始
    threading.Thread(target=monitor_shutdown, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=Config.DEBUG)
