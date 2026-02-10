"""
Settings management services

DEPRECATED: This module is kept for interface compliance but is no longer actively used.
The application now uses direct JSON file management via user_config.py for settings persistence.

Legacy classes:
- QtSettingsManager: Original QSettings-based settings manager (replaced by JSON config)
- DefaultMetadataProvider: Legacy metadata defaults provider (replaced by template system)

For current settings management, see:
- src/services/user_config.py for configuration file management
- src/gui/app.py SettingsCompat class for settings access
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from PyQt6.QtCore import QSettings

from ..core.interfaces import SettingsManager, SettingsError


class QtSettingsManager(SettingsManager):
    """Settings manager using Qt's QSettings for persistence"""
    
    DEFAULT_SETTINGS = {
        'api': {
            'token': '',
            'sandbox': True
        },
        'metadata': {
            'upload_type': 'dataset',
            'access_right': 'open',
            'license': 'cc-by-4.0'
        },
        'ui': {
            'window_geometry': None,
            'tab_index': 0,
            'validate_on_upload': True
        },
        'upload': {
            'auto_publish': False,
            'show_progress_details': True,
            'timeout_seconds': 300
        }
    }
    
    def __init__(self, organization: str = "ZenodoUploader", 
                 application: str = "ElectronDiffraction"):
        """
        Initialize settings manager
        
        Args:
            organization: Organization name for settings
            application: Application name for settings
        """
        self.settings = QSettings(organization, application)
        self._cache = {}
        self._load_cache()
    
    def load_settings(self) -> Dict[str, Any]:
        """Load all application settings"""
        try:
            self._load_cache()
            return self._cache.copy()
        except Exception as e:
            raise SettingsError(f"Failed to load settings: {e}")
    
    def save_settings(self, settings: Dict[str, Any]) -> None:
        """Save application settings"""
        try:
            self._cache = settings.copy()
            self._save_cache()
        except Exception as e:
            raise SettingsError(f"Failed to save settings: {e}")
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a specific setting value using dot notation
        
        Args:
            key: Setting key (e.g., 'api.token', 'ui.window_geometry')
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        try:
            # Use Qt's native getValue for type safety
            qt_default = self._get_default_for_key(key)
            return self.settings.value(key, qt_default if default is None else default)
        except Exception as e:
            if default is not None:
                return default
            raise SettingsError(f"Failed to get setting '{key}': {e}")
    
    def set_setting(self, key: str, value: Any) -> None:
        """
        Set a specific setting value
        
        Args:
            key: Setting key
            value: Value to set
        """
        try:
            self.settings.setValue(key, value)
            self._update_cache_key(key, value)
        except Exception as e:
            raise SettingsError(f"Failed to set setting '{key}': {e}")
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults"""
        try:
            self.settings.clear()
            self._cache = self._flatten_dict(self.DEFAULT_SETTINGS).copy()
            for key, value in self._cache.items():
                self.settings.setValue(key, value)
        except Exception as e:
            raise SettingsError(f"Failed to reset settings: {e}")
    
    def export_settings(self, file_path: str) -> None:
        """
        Export settings to a JSON file
        
        Args:
            file_path: Path to export file
        """
        try:
            settings_dict = self.load_settings()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(settings_dict, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise SettingsError(f"Failed to export settings: {e}")
    
    def import_settings(self, file_path: str, merge: bool = True) -> None:
        """
        Import settings from a JSON file
        
        Args:
            file_path: Path to import file
            merge: Whether to merge with existing settings or replace
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_settings = json.load(f)
            
            if merge:
                current_settings = self.load_settings()
                current_settings.update(imported_settings)
                self.save_settings(current_settings)
            else:
                self.save_settings(imported_settings)
        except Exception as e:
            raise SettingsError(f"Failed to import settings: {e}")
    
    def _load_cache(self) -> None:
        """Load settings into cache"""
        self._cache = {}
        
        # Load defaults first
        defaults = self._flatten_dict(self.DEFAULT_SETTINGS)
        
        # Load all keys from QSettings
        for key in defaults.keys():
            value = self.settings.value(key, defaults[key])
            self._cache[key] = value
    
    def _save_cache(self) -> None:
        """Save cache to QSettings"""
        for key, value in self._cache.items():
            self.settings.setValue(key, value)
        self.settings.sync()
    
    def _update_cache_key(self, key: str, value: Any) -> None:
        """Update a specific key in cache"""
        self._cache[key] = value
    
    def _get_default_for_key(self, key: str) -> Any:
        """Get default value for a key"""
        defaults = self._flatten_dict(self.DEFAULT_SETTINGS)
        return defaults.get(key)
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '') -> Dict[str, Any]:
        """Flatten nested dictionary with dot notation keys"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key).items())
            else:
                items.append((new_key, v))
        return dict(items)


class DefaultMetadataProvider:
    """Provides default metadata from configuration files"""
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize provider
        
        Args:
            base_path: Base path for configuration files
        """
        self.base_path = base_path or Path(__file__).parent.parent.parent
        self.default_file = self.base_path / "templates" / "default_metadata.json"
    
    def get_default_metadata(self) -> Dict[str, Any]:
        """
        Load default metadata from file
        
        Returns:
            Default metadata dictionary
        """
        if not self.default_file.exists():
            return self._get_builtin_defaults()
        
        try:
            with open(self.default_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load default metadata from {self.default_file}: {e}")
            return self._get_builtin_defaults()
    
    def save_default_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Save default metadata to file
        
        Args:
            metadata: Metadata to save as defaults
        """
        try:
            # Ensure directory exists
            self.default_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.default_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise SettingsError(f"Failed to save default metadata: {e}")
    
    def _get_builtin_defaults(self) -> Dict[str, Any]:
        """Get built-in default metadata"""
        return {
            "title": "",
            "description": "",
            "upload_type": "dataset",
            "access_right": "open",
            "license": "cc-by-4.0",
            "creators": [
                {
                    "name": "",
                    "affiliation": "",
                    "orcid": ""
                }
            ],
            "keywords": ["electron diffraction", "crystallography"],
            "communities": [{"identifier": "microed"}],
            "notes": "",
            "ed_parameters": {
                "instrument": "",
                "detector": "",
                "collection_mode": "",
                "voltage": "",
                "wavelength": "",
                "exposure_time": "",
                "rotation_range": "",
                "temperature": "",
                "crystal_size": "",
                "sample_composition": ""
            }
        }