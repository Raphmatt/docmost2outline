"""Environment variable loader utility."""

import os
import sys
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    print(
        "Warning: python-dotenv not installed. Install with: uv add python-dotenv"
    )
    load_dotenv = None


def load_env_vars() -> None:
    """Load environment variables from .env file if it exists."""
    if load_dotenv is None:
        return

    # Try to find .env file in project root
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)


def get_outline_url(fallback: Optional[str] = None) -> str:
    """Get Outline URL from environment or fallback."""
    load_env_vars()
    url = os.getenv("OUTLINE_URL", fallback)

    if not url:
        print("Error: OUTLINE_URL not set in environment or .env file")
        print("Please set OUTLINE_URL or create a .env file (see .env.example)")
        sys.exit(1)

    return url.rstrip("/")


def get_outline_api_key(fallback: Optional[str] = None) -> str:
    """Get Outline API key from environment or fallback."""
    load_env_vars()
    api_key = os.getenv("OUTLINE_API_KEY", fallback)

    if not api_key:
        print("Error: OUTLINE_API_KEY not set in environment or .env file")
        print(
            "Please set OUTLINE_API_KEY or create a .env file (see .env.example)"
        )
        sys.exit(1)

    return api_key
