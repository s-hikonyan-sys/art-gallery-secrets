"""ルーティングパッケージ.

各機能ごとのブループリントをまとめ、外部から利用しやすくします。"""

from .health import health_bp
from .secrets_routes import secrets_bp

__all__ = ["health_bp", "secrets_bp"]
