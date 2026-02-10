"""
Service factory for dependency injection

This factory creates and wires together all the services needed by the application,
implementing a simple dependency injection pattern.
"""

from typing import Optional

from ..core.interfaces import (
    RepositoryAPI, FileValidator, MetadataValidator, 
    UploadService
)
from ..api import ZenodoRepositoryAPI
from ..services import (
    ZenodoFileValidator, ZenodoMetadataValidator,
    UploadManager, TemplateService
)


class ServiceFactory:
    """
    Factory for creating and configuring application services
    
    This implements a simple dependency injection pattern to manage
    service creation and dependencies.
    """
    
    def __init__(self):
        """Initialize the service factory"""
        self._services = {}
        self._initialized = False
    
    def create_services(self, api_token: str = "", sandbox: bool = True) -> None:
        """
        Create and configure all application services
        
        Args:
            api_token: Zenodo API access token
            sandbox: Whether to use sandbox mode
        """
        # Core services
        self._services['file_validator'] = ZenodoFileValidator()
        self._services['metadata_validator'] = ZenodoMetadataValidator()
        self._services['template_service'] = TemplateService()
        
        # API service (conditionally created based on token)
        if api_token:
            self._services['repository_api'] = ZenodoRepositoryAPI(
                access_token=api_token,
                sandbox=sandbox
            )
            
            # Upload service (depends on API and validators)
            self._services['upload_service'] = UploadManager(
                repository_api=self._services['repository_api'],
                file_validator=self._services['file_validator'],
                metadata_validator=self._services['metadata_validator']
            )
        
        self._initialized = True
    
    def update_api_config(self, api_token: str, sandbox: bool) -> None:
        """
        Update API configuration
        
        Args:
            api_token: New API access token
            sandbox: Whether to use sandbox mode
        """
        # Ensure core services (validators, settings) exist before updating API
        self._ensure_initialized()

        if api_token:
            self._services['repository_api'] = ZenodoRepositoryAPI(
                access_token=api_token,
                sandbox=sandbox
            )
            
            # Recreate upload service with new API
            self._services['upload_service'] = UploadManager(
                repository_api=self._services['repository_api'],
                file_validator=self._services['file_validator'],
                metadata_validator=self._services['metadata_validator']
            )
        else:
            # Remove API-dependent services if no token
            self._services.pop('repository_api', None)
            self._services.pop('upload_service', None)
    
    def get_file_validator(self) -> FileValidator:
        """Get the file validator service"""
        self._ensure_initialized()
        return self._services['file_validator']
    
    def get_metadata_validator(self) -> MetadataValidator:
        """Get the metadata validator service"""
        self._ensure_initialized()
        return self._services['metadata_validator']
    
    def get_template_service(self) -> 'TemplateService':
        """Get the template service"""
        self._ensure_initialized()
        return self._services['template_service']
    
    def get_repository_api(self) -> Optional[RepositoryAPI]:
        """Get the repository API service (may be None if no token)"""
        self._ensure_initialized()
        return self._services.get('repository_api')
    
    def get_upload_service(self) -> Optional[UploadService]:
        """Get the upload service (may be None if no API)"""
        self._ensure_initialized()
        return self._services.get('upload_service')
    
    def has_api_services(self) -> bool:
        """Check if API-dependent services are available"""
        self._ensure_initialized()
        return 'repository_api' in self._services
    
    def _ensure_initialized(self) -> None:
        """Ensure services are initialized"""
        if not self._initialized:
            self.create_services()


# Global service factory instance
_service_factory: Optional[ServiceFactory] = None

def get_service_factory() -> ServiceFactory:
    """
    Get the global service factory instance
    
    Returns:
        ServiceFactory instance
    """
    global _service_factory
    if _service_factory is None:
        _service_factory = ServiceFactory()
    return _service_factory


def initialize_services(api_token: str = "", sandbox: bool = True) -> None:
    """
    Initialize global services
    
    Args:
        api_token: Zenodo API access token
        sandbox: Whether to use sandbox mode
    """
    factory = get_service_factory()
    factory.create_services(api_token, sandbox)