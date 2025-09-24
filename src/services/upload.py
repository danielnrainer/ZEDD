"""
Upload services

Manages the complete upload workflow including validation, progress tracking,
and error handling.
"""

import threading
from typing import Dict, Any, Optional, Callable
from pathlib import Path
from enum import Enum

from ..core.interfaces import (
    UploadService, RepositoryAPI, FileValidator, MetadataValidator,
    ProgressCallback, StatusCallback, UploadError
)


class UploadStatus(Enum):
    """Upload status enumeration"""
    IDLE = "idle"
    VALIDATING = "validating"
    CREATING_DEPOSITION = "creating_deposition"
    UPLOADING = "uploading"
    PUBLISHING = "publishing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class UploadManager(UploadService):
    """
    Manages the complete upload workflow
    
    This service orchestrates file validation, metadata validation,
    deposition creation, file upload, and publishing.
    """
    
    def __init__(self, 
                 repository_api: RepositoryAPI,
                 file_validator: FileValidator,
                 metadata_validator: MetadataValidator):
        """
        Initialize upload manager
        
        Args:
            repository_api: API for repository interactions
            file_validator: File validation service
            metadata_validator: Metadata validation service
        """
        self.repository_api = repository_api
        self.file_validator = file_validator
        self.metadata_validator = metadata_validator
        
        self._status = UploadStatus.IDLE
        self._cancel_requested = False
        self._upload_thread: Optional[threading.Thread] = None
        self._current_deposition_id: Optional[int] = None
        
        # Thread safety
        self._lock = threading.Lock()
    
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
        with self._lock:
            if self._status != UploadStatus.IDLE:
                raise UploadError("Upload already in progress")
            
            self._status = UploadStatus.VALIDATING
            self._cancel_requested = False
            self._current_deposition_id = None
        
        try:
            return self._perform_upload(
                metadata, file_path, publish, 
                progress_callback, status_callback
            )
        except Exception as e:
            with self._lock:
                self._status = UploadStatus.FAILED
            raise UploadError(f"Upload failed: {str(e)}") from e
        finally:
            with self._lock:
                if self._status not in [UploadStatus.COMPLETED, UploadStatus.CANCELLED]:
                    self._status = UploadStatus.IDLE
    
    def upload_async(self,
                     metadata: Dict[str, Any], 
                     file_path: str,
                     publish: bool = False,
                     progress_callback: Optional[ProgressCallback] = None,
                     status_callback: Optional[StatusCallback] = None,
                     completion_callback: Optional[Callable[[bool, Any], None]] = None) -> None:
        """
        Upload a file asynchronously
        
        Args:
            metadata: Upload metadata
            file_path: Path to file to upload
            publish: Whether to publish immediately
            progress_callback: Optional progress reporting callback
            status_callback: Optional status update callback
            completion_callback: Callback for completion (success: bool, result: Any)
        """
        def upload_worker():
            try:
                result = self.upload(
                    metadata, file_path, publish,
                    progress_callback, status_callback
                )
                if completion_callback:
                    completion_callback(True, result)
            except Exception as e:
                if completion_callback:
                    completion_callback(False, e)
        
        with self._lock:
            if self._upload_thread and self._upload_thread.is_alive():
                raise UploadError("Upload already in progress")
            
            self._upload_thread = threading.Thread(target=upload_worker, daemon=True)
            self._upload_thread.start()
    
    def cancel_upload(self) -> None:
        """Cancel any ongoing upload operation"""
        with self._lock:
            if self._status == UploadStatus.IDLE:
                return
            
            self._cancel_requested = True
            self._status = UploadStatus.CANCELLED
    
    def is_uploading(self) -> bool:
        """Check if an upload is currently in progress"""
        with self._lock:
            return self._status not in [UploadStatus.IDLE, UploadStatus.COMPLETED, 
                                       UploadStatus.CANCELLED, UploadStatus.FAILED]
    
    def get_status(self) -> UploadStatus:
        """Get current upload status"""
        with self._lock:
            return self._status
    
    def _perform_upload(self,
                        metadata: Dict[str, Any], 
                        file_path: str,
                        publish: bool,
                        progress_callback: Optional[ProgressCallback],
                        status_callback: Optional[StatusCallback]) -> Dict[str, Any]:
        """Perform the actual upload workflow"""
        
        # Step 1: Validate file (5%)
        self._update_status(status_callback, "Validating file...")
        self._update_progress(progress_callback, 5)
        
        if self._cancel_requested:
            return self._handle_cancellation()
        
        file_valid, file_error = self.file_validator.validate(file_path)
        if not file_valid:
            raise UploadError(f"File validation failed: {file_error}")
        
        # Step 2: Validate metadata (10%)
        self._update_status(status_callback, "Validating metadata...")
        self._update_progress(progress_callback, 10)
        
        if self._cancel_requested:
            return self._handle_cancellation()
        
        metadata_valid, metadata_errors = self.metadata_validator.validate(metadata)
        if not metadata_valid:
            error_msg = "Metadata validation failed:\n" + "\n".join(metadata_errors)
            raise UploadError(error_msg)
        
        # Step 3: Create deposition (20%)
        with self._lock:
            self._status = UploadStatus.CREATING_DEPOSITION
        
        self._update_status(status_callback, "Creating deposition...")
        self._update_progress(progress_callback, 20)
        
        if self._cancel_requested:
            return self._handle_cancellation()
        
        deposition = self.repository_api.create_deposition(metadata)
        deposition_id = deposition['id']
        
        with self._lock:
            self._current_deposition_id = deposition_id
        
        # Step 4: Upload file (20-85%)
        with self._lock:
            self._status = UploadStatus.UPLOADING
        
        self._update_status(status_callback, "Uploading file...")
        
        def upload_progress_callback(percentage: int):
            """Map file upload progress to overall progress (20-85%)"""
            if self._cancel_requested:
                return
            overall_progress = 20 + int((percentage * 65) / 100)
            self._update_progress(progress_callback, overall_progress)
        
        if self._cancel_requested:
            return self._handle_cancellation()
        
        file_result = self.repository_api.upload_file(
            deposition_id, file_path, upload_progress_callback
        )
        
        # Step 5: Publish if requested (85-100%)
        if publish:
            with self._lock:
                self._status = UploadStatus.PUBLISHING
            
            self._update_status(status_callback, "Publishing deposition...")
            self._update_progress(progress_callback, 90)
            
            if self._cancel_requested:
                return self._handle_cancellation()
            
            result = self.repository_api.publish_deposition(deposition_id)
            
            self._update_progress(progress_callback, 100)
            self._update_status(status_callback, "Upload completed and published!")
        else:
            result = deposition
            self._update_progress(progress_callback, 100)
            self._update_status(status_callback, "Upload completed (draft)!")
        
        # Mark as completed
        with self._lock:
            self._status = UploadStatus.COMPLETED
            self._current_deposition_id = None
        
        return result
    
    def _handle_cancellation(self) -> Dict[str, Any]:
        """Handle upload cancellation"""
        with self._lock:
            self._status = UploadStatus.CANCELLED
            # Note: We could add cleanup logic here (e.g., delete incomplete deposition)
            self._current_deposition_id = None
        
        raise UploadError("Upload cancelled by user")
    
    def _update_progress(self, callback: Optional[ProgressCallback], percentage: int) -> None:
        """Safely update progress"""
        if callback and not self._cancel_requested:
            try:
                callback(percentage)
            except Exception:
                pass  # Don't let callback errors break the upload
    
    def _update_status(self, callback: Optional[StatusCallback], message: str) -> None:
        """Safely update status"""
        if callback and not self._cancel_requested:
            try:
                callback(message)
            except Exception:
                pass  # Don't let callback errors break the upload


class BatchUploadManager:
    """Manages uploading multiple files as separate depositions"""
    
    def __init__(self, upload_manager: UploadManager):
        """
        Initialize batch upload manager
        
        Args:
            upload_manager: Single file upload manager
        """
        self.upload_manager = upload_manager
    
    def upload_multiple(self,
                        files_and_metadata: list[tuple[str, Dict[str, Any]]],
                        publish: bool = False,
                        progress_callback: Optional[ProgressCallback] = None,
                        status_callback: Optional[StatusCallback] = None) -> list[Dict[str, Any]]:
        """
        Upload multiple files
        
        Args:
            files_and_metadata: List of (file_path, metadata) tuples
            publish: Whether to publish all depositions
            progress_callback: Overall progress callback
            status_callback: Status update callback
            
        Returns:
            List of upload results
        """
        results = []
        total_files = len(files_and_metadata)
        
        for i, (file_path, metadata) in enumerate(files_and_metadata):
            file_name = Path(file_path).name
            
            # Update overall status
            self._update_status(
                status_callback, 
                f"Uploading file {i+1}/{total_files}: {file_name}"
            )
            
            # Calculate overall progress
            def file_progress_callback(file_percentage: int):
                overall_percentage = int(((i * 100) + file_percentage) / total_files)
                self._update_progress(progress_callback, overall_percentage)
            
            try:
                result = self.upload_manager.upload(
                    metadata, file_path, publish,
                    file_progress_callback, None  # Use our own status updates
                )
                results.append(result)
            except Exception as e:
                # Continue with other files, but record the error
                results.append({
                    'error': str(e),
                    'file_path': file_path,
                    'failed': True
                })
        
        self._update_progress(progress_callback, 100)
        self._update_status(status_callback, f"Completed uploading {total_files} files")
        
        return results
    
    def _update_progress(self, callback: Optional[ProgressCallback], percentage: int) -> None:
        """Safely update progress"""
        if callback:
            try:
                callback(percentage)
            except Exception:
                pass
    
    def _update_status(self, callback: Optional[StatusCallback], message: str) -> None:
        """Safely update status"""
        if callback:
            try:
                callback(message)
            except Exception:
                pass