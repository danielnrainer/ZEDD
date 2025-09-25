"""
Services package initialization

Provides high-level services for the Zenodo uploader application.
Each service handles a specific concern and can be used independently.
"""

# Core data structures and file handling
from .metadata import Creator, Contributor, EDParameters, ZenodoMetadata, Funding
from .file_packing import create_zip_from_folder, compute_checksums
from .templates import MetadataTemplate, TemplateService, TemplateCreator, TemplateContributor, TemplateFunding, TemplateCommunity, TemplateEDParameters

# File and metadata validation
from .validation import ZenodoFileValidator, BatchFileValidator
from .metadata_validation import ZenodoMetadataValidator

# Settings management
from .settings import QtSettingsManager, DefaultMetadataProvider

# Upload management
from .upload import UploadManager, BatchUploadManager, UploadStatus

# Service factory for dependency injection
from .factory import ServiceFactory, get_service_factory, initialize_services

# Make key classes available at package level
__all__ = [
    'ZenodoFileValidator',
    'BatchFileValidator', 
    'ZenodoMetadataValidator',
    'QtSettingsManager',
    'DefaultMetadataProvider',
    'UploadManager',
    'BatchUploadManager',
    'UploadStatus',
    'ServiceFactory',
    'get_service_factory',
    'initialize_services'
]