"""Configuration management for the stock analyser."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


# Supported AI providers and their defaults
PROVIDER_DEFAULTS = {
    "gemini": {
        "model": "gemini-2.0-flash",
        "base_url": None,  # Uses google-genai SDK directly
    },
    "groq": {
        "model": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1",
    },
    "openrouter": {
        "model": "google/gemini-2.0-flash-exp:free",
        "base_url": "https://openrouter.ai/api/v1",
    },
}


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    # AI provider: "gemini", "groq", or "openrouter"
    ai_provider: str = "gemini"

    # API keys (only one is needed, based on provider)
    gemini_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""

    # Model override (if not set, uses provider default)
    ai_model: str = ""

    reports_dir: Path = field(default_factory=lambda: Path("reports"))
    screener_base_url: str = "https://www.screener.in"
    yahoo_base_url: str = "https://finance.yahoo.com"

    # Request settings
    request_timeout: int = 30
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )

    @classmethod
    def load(cls, env_file: str | None = None) -> "Config":
        """Load configuration from .env file and environment variables."""
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        provider = os.getenv("AI_PROVIDER", "").lower()

        # Auto-detect provider from available keys if not explicitly set
        if not provider:
            if os.getenv("GROQ_API_KEY"):
                provider = "groq"
            elif os.getenv("OPENROUTER_API_KEY"):
                provider = "openrouter"
            elif os.getenv("GEMINI_API_KEY"):
                provider = "gemini"
            else:
                provider = "gemini"

        return cls(
            ai_provider=provider,
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            ai_model=os.getenv("AI_MODEL", "") or os.getenv("GEMINI_MODEL", ""),
            reports_dir=Path(os.getenv("REPORTS_DIR", "reports")),
        )

    @property
    def active_api_key(self) -> str:
        """Get the API key for the configured provider."""
        keys = {
            "gemini": self.gemini_api_key,
            "groq": self.groq_api_key,
            "openrouter": self.openrouter_api_key,
        }
        return keys.get(self.ai_provider, "")

    @property
    def active_model(self) -> str:
        """Get the model name - uses override or provider default."""
        if self.ai_model:
            return self.ai_model
        defaults = PROVIDER_DEFAULTS.get(self.ai_provider, {})
        return defaults.get("model", "gemini-2.0-flash")

    @property
    def active_base_url(self) -> str | None:
        """Get the base URL for the configured provider."""
        defaults = PROVIDER_DEFAULTS.get(self.ai_provider, {})
        return defaults.get("base_url")

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        key = self.active_api_key
        if not key or key in ("your-gemini-api-key-here", "your-groq-api-key-here", "your-key-here"):
            provider = self.ai_provider
            if provider == "groq":
                errors.append(
                    "GROQ_API_KEY is not set. "
                    "Get your FREE key at https://console.groq.com/keys "
                    "and add it to your .env file."
                )
            elif provider == "openrouter":
                errors.append(
                    "OPENROUTER_API_KEY is not set. "
                    "Get your key at https://openrouter.ai/keys "
                    "and add it to your .env file."
                )
            else:
                errors.append(
                    "GEMINI_API_KEY is not set. "
                    "Get your key at https://aistudio.google.com/apikey "
                    "and add it to your .env file.\n"
                    "  TIP: For a FREE alternative, use Groq instead:\n"
                    "       Get a free key at https://console.groq.com/keys\n"
                    "       Then set GROQ_API_KEY in your .env file."
                )
        return errors
