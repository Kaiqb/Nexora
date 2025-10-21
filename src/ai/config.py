from __future__ import annotations
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, Field

def _detect_device() -> str:
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"

class Settings(BaseSettings):
    # Ollama (preferred if present)
    OLLAMA_HOST: Optional[AnyHttpUrl] = Field("http://localhost:11434", description="Ollama daemon URL")
    OLLAMA_MODEL: Optional[str] = Field("llama3.1:latest", description="Ollama model name")

    # Device & generation tuning
    DEVICE: str = Field(default_factory=_detect_device, description="Runtime device: cuda or cpu")
    MAX_TOKENS: int = 2048
    TEMPERATURE: float = 0.7
    TIMEOUT_SECONDS: int = 120

    # NLU / spaCy
    SPACY_MODEL: str = "en_core_web_trf"

    # Replace class Config with model_config
    model_config = SettingsConfigDict(env_file='.env')

settings = Settings()