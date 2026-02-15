#!/bin/bash
# テスト実行スクリプト

echo "=== Secrets API テスト実行スクリプト ==="
echo ""

# カラー出力の設定
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# PYTHONPATHを設定
export PYTHONPATH=$PYTHONPATH:$(pwd)

echo -e "${GREEN}pytestを実行します...${NC}"
pytest tests/ -v

echo ""
echo "=== テスト完了 ==="
