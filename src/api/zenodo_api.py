"""
Refactored Zenodo API implementation

Focuses purely on API interactions with better separation of concerns.
File upload logic is extracted to a separate service.
"""

import requests
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path

from ..core.interfaces import RepositoryAPI, ProgressCallback, APIError


class ZenodoRepositoryAPI(RepositoryAPI):
    """Zenodo-specific repository API implementation"""
    
    def __init__(self, access_token: str, sandbox: bool = False):
        """
        Initialize Zenodo API client
        
        Args:
            access_token: Zenodo API access token
            sandbox: Whether to use sandbox environment
        """
        self.access_token = access_token
        self.base_url = "https://sandbox.zenodo.org/api" if sandbox else "https://zenodo.org/api"
        
        # Configure session with timeouts and retries
        self.session = requests.Session()
        self.session.params = {'access_token': access_token}
        self.session.timeout = (30, 300)  # (connection_timeout, read_timeout)
        
        adapter = requests.adapters.HTTPAdapter(
            max_retries=requests.adapters.Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[500, 502, 503, 504, 429]
            )
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
    
    def test_metadata(self, metadata: Dict[str, Any]) -> tuple[bool, str, Optional[int]]:
        """
        Test if metadata is accepted by Zenodo by creating and deleting a draft deposition.
        
        This performs a real API test by:
        1. Creating a draft deposition with the metadata
        2. If successful, immediately deleting the draft
        3. Returning success/failure information
        
        Args:
            metadata: Metadata dictionary to test
            
        Returns:
            Tuple of (success, message, deposition_id)
            - success: True if metadata was accepted
            - message: Success message or error description
            - deposition_id: ID of created deposition (None if failed)
        """
        deposition_id = None
        try:
            # Try to create a deposition with this metadata
            url = f"{self.base_url}/deposit/depositions"
            headers = {"Content-Type": "application/json"}
            
            data = {"metadata": metadata}
            response = self.session.post(url, json=data, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            deposition_id = result['id']
            
            # Success! Now clean up by deleting the test deposition
            try:
                self.delete_deposition(deposition_id)
                return (True, f"✅ Metadata accepted by Zenodo! (Test deposition {deposition_id} created and deleted)", deposition_id)
            except:
                # Deletion failed, but metadata was accepted
                return (True, f"✅ Metadata accepted by Zenodo! Note: Test deposition {deposition_id} could not be auto-deleted. Please delete it manually.", deposition_id)
            
        except requests.exceptions.RequestException as e:
            # Extract error details from response
            error_msg = self._extract_metadata_error(e)
            return (False, f"❌ Zenodo rejected the metadata:\n{error_msg}", deposition_id)
        except Exception as e:
            return (False, f"❌ Error testing metadata: {str(e)}", deposition_id)
    
    def _extract_metadata_error(self, error: requests.RequestException) -> str:
        """Extract detailed error information from Zenodo API response"""
        if hasattr(error, 'response') and error.response is not None:
            try:
                error_data = error.response.json()
                if 'errors' in error_data:
                    error_lines = []
                    for err in error_data['errors']:
                        field = err.get('field', 'unknown')
                        message = err.get('messages', [err.get('message', 'unknown error')])
                        if isinstance(message, list):
                            for msg in message:
                                error_lines.append(f"  • {field}: {msg}")
                        else:
                            error_lines.append(f"  • {field}: {message}")
                    return "\n".join(error_lines)
                elif 'message' in error_data:
                    return error_data['message']
            except (ValueError, KeyError):
                pass
        return str(error)
    
    def create_deposition(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new deposition"""
        try:
            url = f"{self.base_url}/deposit/depositions"
            headers = {"Content-Type": "application/json"}
            
            data = {"metadata": metadata}
            response = self.session.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            raise APIError("Request timed out. Please check your connection and try again.")
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "create deposition")
        except Exception as e:
            raise APIError(f"Failed to create deposition: {str(e)}")
    
    def upload_file(self, deposition_id: int, file_path: str, 
                   progress_callback: Optional[ProgressCallback] = None,
                   cancel_checker: Optional[callable] = None) -> Dict[str, Any]:
        """Upload a file to a deposition using the new bucket API
        
        Uses the bucket API as recommended in https://github.com/zenodo/zenodo/issues/833
        This allows uploading files larger than 100MB by streaming binary content.
        
        Implementation follows the pattern from @jakelever and @lnielsen:
        1. Get bucket URL from deposition
        2. PUT file directly to bucket/<filename> with binary stream
        3. Use Authorization Bearer header instead of query params
        
        Args:
            deposition_id: ID of the deposition
            file_path: Path to file to upload
            progress_callback: Optional callback for upload progress
            cancel_checker: Optional function that returns True if upload should be cancelled
        """
        try:
            # Step 1: Get the deposition to extract the bucket URL
            deposition_url = f"{self.base_url}/deposit/depositions/{deposition_id}"
            response = self.session.get(deposition_url)
            response.raise_for_status()
            
            bucket_url = response.json()["links"]["bucket"]
            filename = Path(file_path).name
            
            # Step 2: Upload directly to bucket using PUT
            upload_url = f"{bucket_url}/{filename}"
            
            # Set proper headers as per Zenodo bucket API requirements
            # Using Authorization header instead of query params for better compatibility
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/octet-stream",
                "Authorization": f"Bearer {self.access_token}"
            }
            
            # Step 3: Stream the file content using PUT request
            with ProgressFileWrapper(file_path, progress_callback, cancel_checker) as pf:
                # Note: Don't use session here to avoid adding access_token as query param
                # The bucket API works best with Authorization header only
                response = requests.put(
                    upload_url, 
                    data=pf,
                    headers=headers,
                    timeout=(30, 600)  # Longer timeout for large files
                )
            
            response.raise_for_status()
            return response.json()
            
        except RuntimeError as e:
            if "cancelled" in str(e).lower():
                raise APIError("Upload cancelled by user")
            raise
        except requests.exceptions.Timeout:
            raise APIError("Upload timed out. Please check your connection and try again.")
        except requests.exceptions.RequestException as e:
            self._handle_upload_error(e)
        except Exception as e:
            raise APIError(f"Upload failed: {str(e)}")
    
    def publish_deposition(self, deposition_id: int) -> Dict[str, Any]:
        """Publish a deposition"""
        try:
            url = f"{self.base_url}/deposit/depositions/{deposition_id}/actions/publish"
            response = self.session.post(url)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            raise APIError("Publish request timed out. Please check your connection and try again.")
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "publish deposition")
        except Exception as e:
            raise APIError(f"Failed to publish: {str(e)}")
    
    def get_licenses(self) -> List[Dict[str, Any]]:
        """Get available licenses"""
        try:
            url = f"{self.base_url}/licenses"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "get licenses")
        except Exception as e:
            raise APIError(f"Failed to get licenses: {str(e)}")
    
    def search_communities(self, query: str = "", page: int = 1, size: int = 20) -> List[Dict[str, Any]]:
        """Search for communities"""
        try:
            url = f"{self.base_url}/records"
            params = {
                'q': query,
                'type': 'community',
                'page': page,
                'size': size,
                'communities': '*'
            }
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()['hits']['hits']
            
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "search communities")
        except Exception as e:
            raise APIError(f"Failed to search communities: {str(e)}")
    
    def update_deposition(self, deposition_id: int, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing deposition's metadata"""
        try:
            url = f"{self.base_url}/deposit/depositions/{deposition_id}"
            headers = {"Content-Type": "application/json"}
            
            data = {"metadata": metadata}
            response = self.session.put(url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "update deposition")
        except Exception as e:
            raise APIError(f"Failed to update deposition: {str(e)}")
    
    def get_deposition(self, deposition_id: int) -> Dict[str, Any]:
        """Get an existing deposition"""
        try:
            url = f"{self.base_url}/deposit/depositions/{deposition_id}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "get deposition")
        except Exception as e:
            raise APIError(f"Failed to get deposition: {str(e)}")
    
    def delete_deposition(self, deposition_id: int) -> None:
        """Delete a deposition (only works for unpublished depositions)"""
        try:
            url = f"{self.base_url}/deposit/depositions/{deposition_id}"
            response = self.session.delete(url)
            response.raise_for_status()
            
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "delete deposition")
        except Exception as e:
            raise APIError(f"Failed to delete deposition: {str(e)}")
    
    def delete_deposition_file(self, deposition_id: int, file_id: str) -> None:
        """Delete a file from a deposition"""
        try:
            url = f"{self.base_url}/deposit/depositions/{deposition_id}/files/{file_id}"
            response = self.session.delete(url)
            response.raise_for_status()
            
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, "delete deposition file")
        except Exception as e:
            raise APIError(f"Failed to delete deposition file: {str(e)}")
    
    def list_deposition_files(self, deposition_id: int) -> List[Dict[str, Any]]:
        """List all files in a deposition"""
        try:
            deposition = self.get_deposition(deposition_id)
            return deposition.get('files', [])
            
        except Exception as e:
            raise APIError(f"Failed to list deposition files: {str(e)}")
    
    def list_depositions(self, page: int = 1, size: int = 20) -> List[Dict[str, Any]]:
        """List user depositions"""
        try:
            url = f"{self.base_url}/deposit/depositions"
            params = {'page': page, 'size': size}
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            self._handle_request_error(e, "listing depositions")
            raise APIError(f"Failed to list depositions: {str(e)}")
    
    def test_connection(self) -> bool:
        """Test the API connection"""
        try:
            url = f"{self.base_url}/deposit/depositions"
            response = self.session.get(url)
            response.raise_for_status()
            return True
        except Exception:
            return False
    
    def _handle_request_error(self, error: requests.RequestException, operation: str) -> None:
        """Handle common request errors with user-friendly messages"""
        if hasattr(error, 'response') and error.response is not None:
            status_code = error.response.status_code
            
            if status_code == 401:
                raise APIError("Invalid access token. Please check your API token.")
            elif status_code == 403:
                raise APIError("Insufficient permissions. Please check your token scopes.")
            elif status_code == 400:
                try:
                    error_detail = error.response.json()
                    if 'errors' in error_detail:
                        error_msg = "Validation errors:\n"
                        for err in error_detail['errors']:
                            field = err.get('field', 'unknown')
                            message = err.get('message', 'unknown error')
                            error_msg += f"  - {field}: {message}\n"
                        raise APIError(error_msg)
                except (ValueError, KeyError):
                    pass
                raise APIError(f"Bad request during {operation}. Please check your data.")
            elif status_code == 404:
                raise APIError(f"Resource not found during {operation}.")
            elif status_code == 409:
                raise APIError("Resource conflict. The deposition may be being processed.")
            elif status_code == 429:
                raise APIError("Rate limit exceeded. Please wait a few minutes and try again.")
            elif status_code >= 500:
                raise APIError(f"Server error during {operation}. Please try again later.")
        
        raise APIError(f"Network error during {operation}: {str(error)}")
    
    def _handle_upload_error(self, error: requests.RequestException) -> None:
        """Handle upload-specific errors"""
        if hasattr(error, 'response') and error.response is not None:
            status_code = error.response.status_code
            
            if status_code == 413:
                raise APIError("File too large. Maximum file size is 50GB.")
            elif status_code == 429:
                raise APIError("Rate limit exceeded. Please wait a few minutes and try again.")
        
        self._handle_request_error(error, "upload file")


class ProgressFileWrapper:
    """File wrapper that reports upload progress"""
    
    def __init__(self, file_path: str, progress_callback: Optional[ProgressCallback] = None,
                 cancel_checker: Optional[callable] = None):
        """
        Initialize progress file wrapper
        
        Args:
            file_path: Path to file to wrap
            progress_callback: Optional progress callback
            cancel_checker: Optional function that returns True if upload should be cancelled
        """
        self.file_path = file_path
        self.progress_callback = progress_callback
        self.cancel_checker = cancel_checker
        self.uploaded = 0
        self.total_size = Path(file_path).stat().st_size
        self._file = None
    
    def read(self, chunk_size: int = 8192) -> bytes:
        """Read chunk and update progress"""
        if self._file is None:
            raise RuntimeError("File not opened")
        
        # Check for cancellation before reading next chunk
        if self.cancel_checker and self.cancel_checker():
            # Close file and raise exception to stop the upload
            if self._file:
                self._file.close()
                self._file = None
            raise RuntimeError("Upload cancelled by user")
        
        chunk = self._file.read(chunk_size)
        if chunk:
            self.uploaded += len(chunk)
            if self.progress_callback and self.total_size > 0:
                percentage = min(int((self.uploaded / self.total_size) * 100), 100)
                self.progress_callback(percentage)
        
        return chunk
    
    def __enter__(self):
        """Context manager entry"""
        self._file = open(self.file_path, 'rb')
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self._file:
            self._file.close()
            self._file = None