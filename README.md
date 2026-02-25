# Art Gallery Secrets API

パスワード復号化と配布を行う専用のマイクロサービスです。

## 概要

システム起動時に、事前に Fernet 暗号化された機密情報を復号し、安全なワンタイムトークンを用いて他のコンテナ（backend, database）へパスワードを配布します。

## 主な機能

- **機密情報の復号**: `Fernet`（対称暗号）を使用して、デプロイ時に供給される暗号化済み設定ファイル（`secrets.yaml.encrypted`）を復号します。
- **ワンタイムトークン配布**: 起動時に各サービス専用のランダムトークンを生成し、ファイルとして共有します。
- **セキュリティ認証**: `Authorization: Bearer <token>` ヘッダーによる厳格なトークン検証。
- **自動ライフサイクル管理**:
  - トークンは使用された瞬間に削除され、再利用は不可能です。
  - すべてのトークンが消費された、あるいは起動から5分経過（タイムアウト）すると、プロセス自体が自動的に終了します。

## セキュリティ設計

- **事前暗号化**: 機密情報はデプロイ前に Fernet で暗号化され、GitHub Actions Secrets を経由して配置されます。
- **最小権限**: 各サービスごとに個別のトークンを発行し、必要な情報のみを返却します。
- **攻撃表面の最小化**: 役割を終えた瞬間にプロセスを終了させることで、稼働時間を最小限に抑制します。
- **ネットワーク分離**: Docker 内部ネットワークのみで通信し、ホストや外部からはアクセス不可です。

## シークレットの準備

本サービスで使用する `secrets.yaml.encrypted` は、以下の方法で事前に生成し、GitHub Actions Secrets に登録する必要があります。

### 暗号化済み値の生成

ローカル環境で本リポジトリの `SecretManager` を使用し、値を暗号化します。

```python
from config.secrets import SecretManager

secret_key = "本番用のsecret_key文字列"
db_password = "本番用のDBパスワード"

manager = SecretManager(secret_key=secret_key)
encrypted_password = manager.encrypt(db_password)

print(f"PROD_SECRET_KEY: {secret_key}")
print(f"PROD_DB_PASSWORD_ENCRYPTED: encrypted:{encrypted_password}")
```

### GitHub Actions Secrets への登録

生成された値を、`art-gallery-release-tools` リポジトリの **Settings > Secrets and variables > Actions** に登録してください。

| Secret名 | 内容 |
|---------|------|
| `PROD_SECRET_KEY` | `secret_key` の値（平文） |
| `PROD_DB_PASSWORD_ENCRYPTED` | `encrypted:xxxxx` 形式の Fernet 暗号化済みパスワード |

## 技術スタック

- **Framework**: Flask
- **Security**: Cryptography (Fernet)
- **Testing**: pytest, pytest-cov
- **Linting**: flake8, pylint, mypy, black, isort

## セットアップと実行

### 依存関係のインストール

```bash
pip install -r requirements-dev.txt
```

### テストの実行

```bash
bash tests/run_tests.sh
```

## API エンドポイント

### GET /secrets/database/password

データベースのパスワードを取得します。

- **Header**: `Authorization: Bearer <token>`
- **Response**: `{"password": "..."}`

### GET /health

サービスの稼働状態を確認します（認証不要）。
