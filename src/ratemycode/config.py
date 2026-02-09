
import os
import json
import appdirs
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

APP_NAME = "rateMyCode"
APP_AUTHOR = "RateMyCodeTeam"

# Default Configuration
DEFAULT_CONFIG = {
    "mode": "PROFESSIONAL",
    "voice_enabled": False,
    "max_complexity": 3,
    "gemini_api_key": "",
    "supported_extensions": [".py", ".java", ".js", ".cpp", ".ts", ".go", ".rs"]
}

def get_config_dir():
    return appdirs.user_config_dir(APP_NAME, APP_AUTHOR)

def get_data_dir():
    return appdirs.user_data_dir(APP_NAME, APP_AUTHOR)

def load_config():
    """
    Loads configuration from JSON file in user config dir, falling back to defaults.
    """
    config_dir = get_config_dir()
    config_path = os.path.join(config_dir, "config.json")
    
    config = DEFAULT_CONFIG.copy()
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                config.update(user_config)
        except Exception:
            pass # Keep defaults on error

    # Environment variable override for API Key
    env_key = os.getenv("GEMINI_API_KEY")
    if env_key:
        config["gemini_api_key"] = env_key

    return config

def save_config(config):
    """
    Saves the current configuration to disk.
    """
    config_dir = get_config_dir()
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "config.json")
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
