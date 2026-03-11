from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    provider: str = "openai_compatible"
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    timeout_s: int = 60


class ChunkConfig(BaseModel):
    max_chars: int = 1800
    overlap_chars: int = 200


class RetrievalConfig(BaseModel):
    vectorstore: str = "chroma"
    collection: str = "novelagent_library"
    top_k: int = 8
    chunk: ChunkConfig = Field(default_factory=ChunkConfig)


class AppConfig(BaseModel):
    workspace: str = "./workspace"
    llm: LLMConfig = Field(default_factory=LLMConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    env_workspace = os.getenv("NOVELAGENT_WORKSPACE")
    if config_path is None:
        config_path = Path("novelagent.yaml")

    data: dict[str, Any] = {}
    if config_path.exists():
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        data = _expand_env(raw)

    cfg = AppConfig.model_validate(data)

    if env_workspace:
        cfg.workspace = env_workspace

    def _clean_placeholder(v: str) -> str:
        v = (v or "").strip()
        return "" if (not v or v.startswith("${")) else v

    cfg.llm.base_url = _clean_placeholder(os.getenv("NOVELAGENT_BASE_URL", cfg.llm.base_url or ""))
    cfg.llm.api_key = _clean_placeholder(os.getenv("NOVELAGENT_API_KEY", cfg.llm.api_key or ""))
    cfg.llm.model = _clean_placeholder(os.getenv("NOVELAGENT_MODEL", cfg.llm.model or ""))

    return cfg

