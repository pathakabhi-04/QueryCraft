"""Central configuration. Everything tunable comes from .env (see .env.example)."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PROMPTS_DIR = ROOT / "prompts"
BENCHMARK_PATH = ROOT / "benchmark" / "questions.yaml"
RESULTS_DIR = ROOT / "eval" / "results"
CACHE_DIR = ROOT / "eval" / "cache"

DB_PATH = DATA_DIR / "university.db"
SCHEMA_SQL_PATH = DATA_DIR / "schema.sql"
SCHEMA_DOCS_PATH = DATA_DIR / "schema_docs.yaml"

load_dotenv(ROOT / ".env")


def _env(name: str, default: str = "") -> str:
    # strip inline comments like "groq   # groq | ollama"
    return os.getenv(name, default).split("#")[0].strip()


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    llama_backend: str          # "groq" or "ollama"
    groq_api_key: str
    llama_model: str
    ollama_base_url: str
    ollama_num_ctx: int
    temperature: float
    max_output_tokens: int
    call_delay_seconds: float
    max_api_retries: int
    query_timeout_seconds: float
    row_limit: int


def get_settings() -> Settings:
    return Settings(
        gemini_api_key=_env("GEMINI_API_KEY"),
        gemini_model=_env("GEMINI_MODEL"),
        llama_backend=_env("LLAMA_BACKEND", "groq").lower(),
        groq_api_key=_env("GROQ_API_KEY"),
        llama_model=_env("LLAMA_MODEL"),
        ollama_base_url=_env("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        ollama_num_ctx=int(_env("OLLAMA_NUM_CTX", "8192")),
        temperature=float(_env("TEMPERATURE", "0")),
        max_output_tokens=int(_env("MAX_OUTPUT_TOKENS", "1024")),
        call_delay_seconds=float(_env("CALL_DELAY_SECONDS", "1.0")),
        max_api_retries=int(_env("MAX_API_RETRIES", "5")),
        query_timeout_seconds=float(_env("QUERY_TIMEOUT_SECONDS", "5")),
        row_limit=int(_env("ROW_LIMIT", "500")),
    )
