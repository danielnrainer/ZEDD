"""
User Configuration Management for ZEDD
========================================

Provides cross-platform path management for user configuration and data.
All user-specific data is stored in the OS-appropriate application data directory:

    Windows: %APPDATA%/ZEDD/
    macOS:   ~/Library/Application Support/ZEDD/
    Linux:   ~/.config/ZEDD/

Directory structure:
    ZEDD/
    ├── settings.json           # GUI state and preferences
    ├── tokens.json             # API tokens (sandbox & production)
    ├── user_template.json      # User's custom metadata template (optional)
    └── cif_mappings.json       # User's custom CIF mappings (optional)
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def get_user_config_directory() -> Path:
    """
    Get the ZEDD user configuration directory path.
    
    This is the root directory for all user-specific data.
    
    Returns:
        Path to the configuration directory:
        - Windows: %APPDATA%/ZEDD
        - macOS: ~/Library/Application Support/ZEDD
        - Linux: ~/.config/ZEDD
    """
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
        return Path(base) / 'ZEDD'
    elif sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'ZEDD'
    else:
        # Linux and other Unix-like systems
        xdg_config = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        return Path(xdg_config) / 'ZEDD'


def ensure_user_config_directory() -> Path:
    """
    Ensure the ZEDD configuration directory exists.
    
    Returns:
        Path to the configuration directory.
    """
    config_dir = get_user_config_directory()
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_settings_file_path() -> Path:
    """
    Get the path to the settings JSON file.
    
    Returns:
        Path to settings.json in the config directory
    """
    return ensure_user_config_directory() / 'settings.json'


def get_user_template_path() -> Path:
    """
    Get the path to the user's custom metadata template.
    
    Returns:
        Path to user_template.json in the config directory
    """
    return ensure_user_config_directory() / 'user_template.json'


def get_user_cif_mappings_path() -> Path:
    """
    Get the path to the user's custom CIF mappings.
    
    Returns:
        Path to cif_mappings.json in the config directory
    """
    return ensure_user_config_directory() / 'cif_mappings.json'


def get_tokens_file_path() -> Path:
    """
    Get the path to the tokens JSON file.
    
    Returns:
        Path to tokens.json in the config directory
    """
    return ensure_user_config_directory() / 'tokens.json'


def load_json_config(file_path: Path, default: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Load a JSON configuration file.
    
    Args:
        file_path: Path to JSON file
        default: Default value if file doesn't exist or is invalid
    
    Returns:
        Dictionary from JSON file, or default if file doesn't exist
    """
    if default is None:
        default = {}
    
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load {file_path}: {e}")
    
    return default


def save_json_config(file_path: Path, data: Dict[str, Any]) -> bool:
    """
    Save a dictionary as JSON configuration file.
    
    Args:
        file_path: Path to JSON file
        data: Dictionary to save
    
    Returns:
        True if save succeeded, False otherwise
    """
    try:
        ensure_user_config_directory()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Warning: Could not save {file_path}: {e}")
        return False


def load_settings() -> Dict[str, Any]:
    """
    Load user settings from settings.json.
    
    Returns:
        Dictionary of settings, empty dict if file doesn't exist
    """
    return load_json_config(get_settings_file_path(), {})


def save_settings(settings: Dict[str, Any]) -> bool:
    """
    Save settings to settings.json.
    
    Args:
        settings: Dictionary of settings to save
    
    Returns:
        True if save succeeded, False otherwise
    """
    return save_json_config(get_settings_file_path(), settings)


def load_tokens() -> Dict[str, str]:
    """
    Load API tokens from tokens.json.
    
    Returns:
        Dictionary with 'sandbox' and 'production' tokens, empty strings if not set
    """
    tokens = load_json_config(get_tokens_file_path(), {})
    return {
        'sandbox': tokens.get('sandbox', ''),
        'production': tokens.get('production', '')
    }


def save_tokens(sandbox_token: str = '', production_token: str = '') -> bool:
    """
    Save API tokens to tokens.json.
    
    Args:
        sandbox_token: Zenodo sandbox API token
        production_token: Zenodo production API token
    
    Returns:
        True if save succeeded, False otherwise
    """
    tokens = {
        'sandbox': sandbox_token,
        'production': production_token
    }
    return save_json_config(get_tokens_file_path(), tokens)


def get_bundled_resource_path(relative_path: str) -> Path:
    """
    Get the path to a bundled resource file.
    
    Handles both development and PyInstaller bundled scenarios.
    
    Args:
        relative_path: Path relative to the project/bundle root.
        
    Returns:
        Absolute path to the resource.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        # Development environment - go up from src/services to project root
        base_path = Path(__file__).parent.parent.parent
    
    return base_path / relative_path


def open_user_config_directory() -> bool:
    """
    Open the user config directory in the system file explorer.
    
    Returns:
        True if successful, False otherwise.
    """
    import subprocess
    
    try:
        config_dir = ensure_user_config_directory()
        
        if sys.platform == 'win32':
            os.startfile(str(config_dir))
        elif sys.platform == 'darwin':
            subprocess.run(['open', str(config_dir)], check=True)
        else:
            subprocess.run(['xdg-open', str(config_dir)], check=True)
        
        return True
    except Exception as e:
        print(f"Error opening config directory: {e}")
        return False
