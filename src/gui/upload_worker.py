"""
Refactored upload worker using modular services

This worker is much simpler and focuses only on GUI integration,
delegating the actual work to specialized services.
"""

from PyQt6.QtCore import QThread, pyqtSignal
from typing import Dict, Any, Optional

from ..services import UploadManager, UploadStatus
from ..core.interfaces import ProgressCallback, StatusCallback


class ModularUploadWorker(QThread):
    """
    Simplified upload worker using modular services
    
    This worker acts as a bridge between the GUI and the upload service,
    translating between Qt signals and service callbacks.
    """
    
    # Qt signals
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str) 
    upload_completed = pyqtSignal(dict)
    upload_failed = pyqtSignal(str)
    
    def __init__(self, upload_manager: UploadManager, 
                 metadata: Dict[str, Any],
                 file_path: str,
                 publish: bool = False):
        """
        Initialize upload worker
        
        Args:
            upload_manager: Upload service instance
            metadata: Upload metadata
            file_path: Path to file to upload
            publish: Whether to publish immediately
        """
        super().__init__()
        self.upload_manager = upload_manager
        self.metadata = metadata
        self.file_path = file_path
        self.publish = publish
        self._cancelled = False
    
    def cancel(self):
        """Cancel the upload operation"""
        self._cancelled = True
        self.upload_manager.cancel_upload()
        self.quit()
    
    def run(self):
        """Execute the upload in a separate thread"""
        try:
            # Create callbacks that emit Qt signals
            def progress_callback(percentage: int) -> None:
                if not self._cancelled:
                    self.progress_updated.emit(percentage)
            
            def status_callback(message: str) -> None:
                if not self._cancelled:
                    self.status_updated.emit(message)
            
            # Perform upload using the service
            result = self.upload_manager.upload(
                metadata=self.metadata,
                file_path=self.file_path,
                publish=self.publish,
                progress_callback=progress_callback,
                status_callback=status_callback
            )
            
            if not self._cancelled:
                self.upload_completed.emit(result)
                
        except Exception as e:
            if not self._cancelled:
                self.upload_failed.emit(str(e))