#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$PROJECT_DIR"

echo "[1/5] 拉取 v1.0.0 代码"
git pull --ff-only

echo "[2/5] 校验 Docker Compose 配置"
docker compose config --quiet

echo "[3/5] 重建并启动全部服务"
docker compose up -d --build

echo "[4/5] 等待 FastAPI 就绪"
for _ in $(seq 1 60); do
    if curl -fsS --max-time 3 http://127.0.0.1:8000/openapi.json >/dev/null; then
        break
    fi
    sleep 2
done
curl -fsS --max-time 5 http://127.0.0.1:8000/openapi.json >/dev/null

echo "[5/5] 校验静态页面和容器健康状态"
curl -fsS --max-time 5 http://127.0.0.1:8000/static/index.html \
    | grep -q 'data-tab="logs"'
docker compose ps

echo "部署完成：http://服务器公网IP/"
