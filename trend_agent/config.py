import os
import json
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_API_KEY")
MODEL = os.getenv("MODEL", "gpt-4o-mini")

# Trend Agent Configuration
MAX_TRENDS = int(os.getenv("MAX_TRENDS", "30"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")


# ============================================================================
# Settings Loader for config/settings.json
# ============================================================================

# Cache for loaded settings
_settings_cache = None


def get_settings_path() -> str:
    """Get the path to settings.json file."""
    # Get the project root directory (parent of trend_agent)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    return os.path.join(project_root, 'config', 'settings.json')


def load_settings(force_reload: bool = False) -> Dict[str, Any]:
    """
    Load settings from config/settings.json.

    Args:
        force_reload: If True, reload from file even if cached

    Returns:
        Dictionary of settings with defaults for missing values
    """
    global _settings_cache

    # Return cached settings if available and not forcing reload
    if _settings_cache is not None and not force_reload:
        return _settings_cache

    # Default settings (fallback if file doesn't exist)
    default_settings = {
        'source_diversity': {
            'enabled': True,
            'max_percentage_per_source': 0.20,
        }
    }

    try:
        settings_path = get_settings_path()

        if os.path.exists(settings_path):
            with open(settings_path, 'r') as f:
                file_settings = json.load(f)

            # Merge with defaults (file settings override defaults)
            settings = default_settings.copy()
            settings.update(file_settings)
            _settings_cache = settings
            return settings
        else:
            print(f"Settings file not found at {settings_path}, using defaults")
            _settings_cache = default_settings
            return default_settings

    except Exception as e:
        print(f"Error loading settings: {e}, using defaults")
        _settings_cache = default_settings
        return default_settings


def get_source_diversity_config() -> Dict[str, Any]:
    """
    Get source diversity configuration.

    Returns:
        Dictionary with 'enabled' and 'max_percentage_per_source' keys
    """
    settings = load_settings()
    return settings.get('source_diversity', {
        'enabled': True,
        'max_percentage_per_source': 0.20
    })


def is_source_diversity_enabled() -> bool:
    """Check if source diversity limiting is enabled."""
    config = get_source_diversity_config()
    return config.get('enabled', True)


def get_max_percentage_per_source() -> float:
    """Get the maximum percentage each source can contribute per category."""
    config = get_source_diversity_config()
    return config.get('max_percentage_per_source', 0.20)
