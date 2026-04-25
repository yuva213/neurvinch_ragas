from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    kb_path: Path = Field(default=Path("data/kb"), alias="NEURVINCH_KB_PATH")
    query_log_path: Path = Field(default=Path("data/queries/query_logs.csv"), alias="NEURVINCH_QUERY_LOG_PATH")
    output_dir: Path = Field(default=Path("outputs"), alias="NEURVINCH_OUTPUT_DIR")

    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="NEURVINCH_EMBEDDING_MODEL",
    )
    embedding_backend: str = Field(default="tfidf", alias="NEURVINCH_EMBEDDING_BACKEND")
    nli_model: str = Field(default="cross-encoder/nli-deberta-v3-base", alias="NEURVINCH_NLI_MODEL")
    nli_backend: str = Field(default="heuristic", alias="NEURVINCH_NLI_BACKEND")

    contradiction_threshold: float = Field(default=0.85, alias="NEURVINCH_CONTRADICTION_THRESHOLD")
    void_retrieval_threshold: float = Field(default=0.35, alias="NEURVINCH_VOID_RETRIEVAL_THRESHOLD")
    dbscan_eps: float = Field(default=0.4, alias="NEURVINCH_DBSCAN_EPS")
    dbscan_min_samples: int = Field(default=8, alias="NEURVINCH_DBSCAN_MIN_SAMPLES")

    top_k_candidates: int = 20
    top_k_final: int = 5

    # LLM Configuration
    llm_provider: str = Field(default="groq", alias="NEURVINCH_LLM_PROVIDER")
    llm_api_key: str = Field(default="", alias="GROQ_API_KEY")
    llm_model: str = Field(default="mixtral-8x7b-32768", alias="NEURVINCH_LLM_MODEL")
    llm_temperature: float = Field(default=0.7, alias="NEURVINCH_LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=1024, alias="NEURVINCH_LLM_MAX_TOKENS")


settings = Settings()
