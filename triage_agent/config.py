"""Configuration management for the Triage Memo Agent."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Configuration for the Triage Memo Agent."""

    # LLM settings
    llm_backend: str = Field(default="openclaw")
    llm_model: str = Field(default="claude-sonnet-4-6")
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)

    # API keys (optional when llm_backend=openclaw)
    openai_api_key: str = Field(default="")
    anthropic_api_key: str = Field(default="")
    semantic_scholar_api_key: str = Field(default="")

    # OpenClaw runtime backend settings
    openclaw_llm_agent: str = Field(default="main")
    openclaw_llm_timeout_seconds: float = Field(default=180.0)

    # Output settings
    output_format: str = Field(default="markdown")
    output_dir: Path = Field(default=Path("./output"))

    # Agent tuning
    max_related_papers: int = Field(default=5, ge=1, le=20)
    max_prior_art: int = Field(default=5, ge=1, le=20)

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Load configuration from environment variables."""
        return cls(
            llm_backend=os.getenv("LLM_BACKEND", "openclaw"),
            llm_model=os.getenv("LLM_MODEL", "claude-sonnet-4-6"),
            llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY", ""),
            openclaw_llm_agent=os.getenv("OPENCLAW_LLM_AGENT", "main"),
            openclaw_llm_timeout_seconds=float(
                os.getenv("OPENCLAW_LLM_TIMEOUT_SECONDS", "180")
            ),
            output_format=os.getenv("OUTPUT_FORMAT", "markdown"),
            output_dir=Path(os.getenv("OUTPUT_DIR", "./output")),
        )

    @property
    def has_provider_key(self) -> bool:
        """Check if at least one direct provider API key is configured."""
        return bool(self.openai_api_key or self.anthropic_api_key)

    @property
    def can_run(self) -> bool:
        """Check if at least one backend path is available."""
        backend = self.llm_backend.strip().lower()
        if backend == "openclaw":
            return True
        if backend in {"openai", "anthropic"}:
            return self.has_provider_key
        # auto mode can use either direct provider keys or OpenClaw runtime fallback
        return True
