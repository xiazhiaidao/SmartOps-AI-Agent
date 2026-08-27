FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_ENDPOINT=https://hf-mirror.com \
    HF_HUB_DISABLE_XET=1 \
    DATA_DIR=/app/data

WORKDIR /app

# 系统依赖：build-essential 用于编译部分 Python 包；curl 用于健康检查
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY web ./web
COPY scripts ./scripts
COPY data/knowledge ./data/knowledge

RUN mkdir -p data/uploads data/vector_index data/models data/charts \
    && chmod +x scripts/docker_entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

CMD ["bash", "scripts/docker_entrypoint.sh"]