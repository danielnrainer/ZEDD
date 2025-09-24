"""
Core module initialization
"""

# Make core interfaces available at package level
from .interfaces import (
    ProgressCallback,
    StatusCallback,
    FileValidator,
    MetadataValidator,
    UploadService,
    RepositoryAPI,
    SettingsManager,
    MetadataManager,
    UploadError,
    ValidationError,
    APIError,
    SettingsError
)