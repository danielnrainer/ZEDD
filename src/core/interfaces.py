"""
Core interfaces and protocols for the Zenodo Uploader

This module defines the contracts that different components must implement,
enabling better modularity, testing, and maintainability.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, Protocol
from pathlib import Path


class ProgressCallback(Protocol):
    """Protocol for progress reporting callbacks"""
    def __call__(self, percentage: int) -> None:
        """Report progress as a percentage (0-100)"""
        ...


class StatusCallback(Protocol):
    """Protocol for status update callbacks"""
    def __call__(self, message: str) -> None:
        """Report status message"""
        ...


class FileValidator(ABC):
    """Abstract base class for file validation"""
    
    @abstractmethod
    def validate(self, file_path: str) -> tuple[bool, Optional[str]]:
        """
        Validate a file for upload
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass


class MetadataValidator(ABC):
    """Abstract base class for metadata validation"""
    
    @abstractmethod
    def validate(self, metadata: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate metadata for upload
        
        Args:
            metadata: Metadata dictionary to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        pass


class UploadService(ABC):
    """Abstract base class for upload services"""
    
    @abstractmethod
    def upload(self, 
               metadata: Dict[str, Any], 
               file_path: str,
               publish: bool = False,
               progress_callback: Optional[ProgressCallback] = None,
               status_callback: Optional[StatusCallback] = None) -> Dict[str, Any]:
        """
        Upload a file to the repository
        
        Args:
            metadata: Upload metadata
            file_path: Path to file to upload
            publish: Whether to publish immediately
            progress_callback: Optional progress reporting callback
            status_callback: Optional status update callback
            
        Returns:
            Upload result dictionary
            
        Raises:
            UploadError: If upload fails
        """
        pass
    
    @abstractmethod
    def cancel_upload(self) -> None:
        """Cancel any ongoing upload operation"""
        pass
    
    @abstractmethod
    def is_uploading(self) -> bool:
        """Check if an upload is currently in progress"""
        pass


class RepositoryAPI(ABC):
    """Abstract base class for repository API interactions"""
    
    @abstractmethod
    def create_deposition(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new deposition"""
        pass
    
    @abstractmethod
    def upload_file(self, deposition_id: int, file_path: str, 
                   progress_callback: Optional[ProgressCallback] = None) -> Dict[str, Any]:
        """Upload a file to a deposition"""
        pass
    
    @abstractmethod
    def publish_deposition(self, deposition_id: int) -> Dict[str, Any]:
        """Publish a deposition"""
        pass
    
    @abstractmethod
    def get_licenses(self) -> List[Dict[str, Any]]:
        """Get available licenses"""
        pass
    
    @abstractmethod
    def search_communities(self, query: str = "", page: int = 1, size: int = 20) -> List[Dict[str, Any]]:
        """Search for communities"""
        pass
    
    @abstractmethod
    def list_depositions(self, page: int = 1, size: int = 20) -> List[Dict[str, Any]]:
        """List user depositions (for connection testing)"""
        pass


class SettingsManager(ABC):
    """Abstract base class for settings management"""
    
    @abstractmethod
    def load_settings(self) -> Dict[str, Any]:
        """Load application settings"""
        pass
    
    @abstractmethod
    def save_settings(self, settings: Dict[str, Any]) -> None:
        """Save application settings"""
        pass
    
    @abstractmethod
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific setting value"""
        pass
    
    @abstractmethod
    def set_setting(self, key: str, value: Any) -> None:
        """Set a specific setting value"""
        pass


class MetadataManager(ABC):
    """Abstract base class for metadata management"""
    
    @abstractmethod
    def load_from_json(self, file_path: str) -> Dict[str, Any]:
        """Load metadata from JSON file"""
        pass
    
    @abstractmethod
    def save_to_json(self, metadata: Dict[str, Any], file_path: str) -> None:
        """Save metadata to JSON file"""
        pass
    
    @abstractmethod
    def get_default_metadata(self) -> Dict[str, Any]:
        """Get default metadata template"""
        pass
    
    @abstractmethod
    def validate_metadata(self, metadata: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate metadata structure and content"""
        pass


# Custom exceptions
class UploadError(Exception):
    """Raised when upload operations fail"""
    pass


class ValidationError(Exception):
    """Raised when validation fails"""
    pass


class APIError(Exception):
    """Raised when API operations fail"""
    pass


class SettingsError(Exception):
    """Raised when settings operations fail"""
    pass