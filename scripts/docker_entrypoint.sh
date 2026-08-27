#!/bin/sh
set -e

# 首次启动（空 volume）时自动生成示例数据 + 知识库向量索引
if [ ! -f data/orders.csv ] || [ ! -f data/devices.csv ] || [ ! -f data/vector_index/chunks.json ]; then
  echo "[entrypoint] 未检测到示例数据/向量索引，首次启动自动生成..."
  python scripts/seed_data.py
fi

echo "[entrypoint] 启动 SmartOps-AI-Agent..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000