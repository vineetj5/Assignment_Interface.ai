from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load .env file from project root if present
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class AgentSettings(BaseModel):
    groq_api_key: str = Field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    groq_model: str = Field(default_factory=lambda: os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"))
    target_url: str = Field(default_factory=lambda: os.getenv("TARGET_URL", "http://127.0.0.1:8000"))

    max_steps: int = 15
    overall_timeout_seconds: int = 120
    max_consecutive_failures: int = 3
    same_observation_limit: int = 3
    reprompt_on_invalid_decision: bool = True
