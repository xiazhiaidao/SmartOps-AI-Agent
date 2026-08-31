"""应用配置：从 .env 读取，支持环境变量覆盖。

所有可调参数集中在这里，便于私有化部署时按需调整。
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------- 应用基础信息 ----------
    app_name: str = "SmartOps-AI-Agent"
    app_version: str = "2.0.0"
    environment: str = "development"  # development / test / production
    log_level: str = "INFO"

    # CORS：逗号分隔的 Origin 列表；`*` 表示允许所有来源
    cors_origins: str = "*"

    # ---------- LLM 网关（OpenAI 兼容） ----------
    llm_base_url: str = "https://tokenrhythm.studio/v1"
    llm_api_key: str = ""
    llm_model: str = "deepseek-v4-flash"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2048
    llm_timeout: float = 60.0

    # ---------- 文件上传 ----------
    upload_max_size_mb: int = 20

    # ---------- RAG ----------
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_dim: int = 512
    top_k: int = 4
    score_threshold: float = 0.35
    chunk_size: int = 500
    chunk_overlap: int = 80

    # Hugging Face 镜像（国内/受限网络环境），并禁用 Xet 通道
    hf_endpoint: str = "https://hf-mirror.com"
    hf_hub_disable_xet: bool = True

    # ---------- 数据目录 ----------
    data_dir: Path = Path("./data")

    # 兼容旧项目已下载好的 BGE 缓存（避免重复下载 ~100MB）
    reuse_external_model_cache: bool = True
    external_model_cache: Path = Path("../deepseek-rag-qa/data/models")

    @property
    def knowledge_dir(self) -> Path:
        return Path(self.data_dir) / "knowledge"

    @property
    def vector_index_dir(self) -> Path:
        return Path(self.data_dir) / "vector_index"

    @property
    def model_cache_dir(self) -> Path:
        return Path(self.data_dir) / "models"

    @property
    def charts_dir(self) -> Path:
        return Path(self.data_dir) / "charts"

    @property
    def uploads_dir(self) -> Path:
        return Path(self.data_dir) / "uploads"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def orders_csv(self) -> Path:
        return Path(self.data_dir) / "orders.csv"

    @property
    def devices_csv(self) -> Path:
        return Path(self.data_dir) / "devices.csv"


settings = Settings()
