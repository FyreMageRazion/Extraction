"""
Configuration management for the support desk voice agent.
"""

import os
from typing import Any, Dict

from dotenv import load_dotenv
from pathlib import Path

# Load .env from root directory or src/ directory
root_env = Path(__file__).parent.parent / ".env"
src_env = Path(__file__).parent / ".env"

if root_env.exists():
    load_dotenv(root_env)
elif src_env.exists():
    load_dotenv(src_env)
else:
    # Fallback to default behavior (current directory)
    load_dotenv()


class Config:
    """Application configuration class."""
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables with defaults."""
        return {
            "azure_voicelive_api_key": os.getenv("AZURE_VOICELIVE_API_KEY", ""),
            "azure_voicelive_endpoint": os.getenv(
                "AZURE_VOICELIVE_ENDPOINT",
                "wss://api.voicelive.com/v1"
            ),
            "voicelive_model": os.getenv("VOICELIVE_MODEL", "gpt-4o-realtime-preview"),
            "voicelive_voice": os.getenv("VOICELIVE_VOICE", "en-US-JennyNeural"),
            "database_path": os.getenv("DATABASE_PATH", "data/tickets.db"),
            "instructions": os.getenv("VOICELIVE_INSTRUCTIONS"),  # Optional custom instructions
            "recording_dir": os.getenv("RECORDING_DIR", "recordings"),  # Directory for conversation recordings
        }
    
    def __getitem__(self, key: str) -> Any:
        """Get configuration value by key."""
        return self._config.get(key)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with optional default."""
        return self._config.get(key, default)
    
    @property
    def as_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary."""
        return self._config.copy()


config = Config()
