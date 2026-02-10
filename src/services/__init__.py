"""
Services package initialization

Provides high-level services for the Zenodo uploader application.
Each service handles a specific concern and can be used independently.
"""

# Core data structures and file handling
from .metadata import Creator, Contributor, EDParameters, ZenodoMetadata, Funding
from .file_packing import create_zip_from_folder, compute_checksums
from .templates import MetadataTemplate, TemplateService, TemplateCreator, TemplateContributor, TemplateFunding, TemplateCommunity, TemplateEDParameters

# CIF file parsing
from .cif_parser import CIFParser, CIFData, extract_parameters_from_cif, parse_multiple_cifs, CIF_TO_PARAMETER_MAPPING

# User configuration and settings location
from .user_config import (
    get_user_config_directory, ensure_user_config_directory, 
    get_settings_file_path, get_user_template_path, get_user_cif_mappings_path,
    get_tokens_file_path, load_tokens, save_tokens,
    load_settings, save_settings, load_json_config, save_json_config,
    get_bundled_resource_path, open_user_config_directory
)

# File and metadata validation
from .validation import ZenodoFileValidator, BatchFileValidator
from .metadata_validation import ZenodoMetadataValidator

# Upload management
from .upload import UploadManager, BatchUploadManager, UploadStatus

# Service factory for dependency injection
from .factory import ServiceFactory, get_service_factory, initialize_services

# Make key classes available at package level
__all__ = [
    'ZenodoFileValidator',
    'BatchFileValidator', 
    'ZenodoMetadataValidator',
    'UploadManager',
    'BatchUploadManager',
    'UploadStatus',
    'ServiceFactory',
    'get_service_factory',
    'initialize_services',
    'CIFParser',
    'CIFData',
    'extract_parameters_from_cif',
    'parse_multiple_cifs',
    'CIF_TO_PARAMETER_MAPPING',
    'get_user_config_directory',
    'ensure_user_config_directory',
    'get_settings_file_path',
    'get_user_template_path',
    'get_user_cif_mappings_path',
    'load_settings',
    'save_settings',
    'load_json_config',
    'save_json_config',
    'get_bundled_resource_path',
    'open_user_config_directory'
]