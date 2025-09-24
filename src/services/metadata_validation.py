"""
Metadata validation services

Provides validation for upload metadata to ensure compliance with
repository requirements and data quality standards.
"""

from typing import Dict, Any, List, Tuple, Optional
import re
from datetime import datetime

from ..core.interfaces import MetadataValidator, ValidationError


class ZenodoMetadataValidator(MetadataValidator):
    """Metadata validator for Zenodo uploads"""
    
    # Required fields
    REQUIRED_FIELDS = {
        'title': str,
        'description': str,
        'creators': list,
        'upload_type': str
    }
    
    # Valid upload types
    VALID_UPLOAD_TYPES = {
        'publication', 'poster', 'presentation', 'dataset', 
        'image', 'video', 'software', 'lesson', 'physicalobject', 'other'
    }
    
    # Valid access rights
    VALID_ACCESS_RIGHTS = {'open', 'embargoed', 'restricted', 'closed'}
    
    def validate(self, metadata: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate metadata for Zenodo upload
        
        Args:
            metadata: Metadata dictionary to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check required fields
        for field, expected_type in self.REQUIRED_FIELDS.items():
            if field not in metadata:
                errors.append(f"Required field missing: {field}")
                continue
            
            if not isinstance(metadata[field], expected_type):
                errors.append(f"Field '{field}' must be of type {expected_type.__name__}")
        
        # Validate specific fields
        errors.extend(self._validate_title(metadata.get('title')))
        errors.extend(self._validate_description(metadata.get('description')))
        errors.extend(self._validate_creators(metadata.get('creators')))
        errors.extend(self._validate_upload_type(metadata.get('upload_type')))
        errors.extend(self._validate_access_right(metadata.get('access_right')))
        errors.extend(self._validate_keywords(metadata.get('keywords')))
        errors.extend(self._validate_communities(metadata.get('communities')))
        errors.extend(self._validate_publication_date(metadata.get('publication_date')))
        
        return len(errors) == 0, errors
    
    def _validate_title(self, title: Any) -> List[str]:
        """Validate title field"""
        errors = []
        if not isinstance(title, str):
            return errors  # Type error already caught
        
        if not title.strip():
            errors.append("Title cannot be empty")
        elif len(title.strip()) < 3:
            errors.append("Title must be at least 3 characters long")
        elif len(title) > 250:
            errors.append("Title cannot exceed 250 characters")
        
        return errors
    
    def _validate_description(self, description: Any) -> List[str]:
        """Validate description field"""
        errors = []
        if not isinstance(description, str):
            return errors  # Type error already caught
        
        if not description.strip():
            errors.append("Description cannot be empty")
        elif len(description.strip()) < 10:
            errors.append("Description must be at least 10 characters long")
        
        return errors
    
    def _validate_creators(self, creators: Any) -> List[str]:
        """Validate creators field"""
        errors = []
        if not isinstance(creators, list):
            return errors  # Type error already caught
        
        if not creators:
            errors.append("At least one creator is required")
            return errors
        
        for i, creator in enumerate(creators):
            if not isinstance(creator, dict):
                errors.append(f"Creator {i+1} must be a dictionary")
                continue
            
            # Check required creator fields
            if 'name' not in creator:
                errors.append(f"Creator {i+1} missing required 'name' field")
            elif not creator['name'].strip():
                errors.append(f"Creator {i+1} name cannot be empty")
            
            # Validate ORCID if present
            if 'orcid' in creator and creator['orcid']:
                if not self._is_valid_orcid(creator['orcid']):
                    errors.append(f"Creator {i+1} has invalid ORCID format")
        
        return errors
    
    def _validate_upload_type(self, upload_type: Any) -> List[str]:
        """Validate upload_type field"""
        errors = []
        if not isinstance(upload_type, str):
            return errors
        
        if upload_type not in self.VALID_UPLOAD_TYPES:
            errors.append(f"Invalid upload_type '{upload_type}'. "
                         f"Must be one of: {', '.join(sorted(self.VALID_UPLOAD_TYPES))}")
        
        return errors
    
    def _validate_access_right(self, access_right: Any) -> List[str]:
        """Validate access_right field"""
        errors = []
        if access_right is None:
            return errors  # Optional field
        
        if not isinstance(access_right, str):
            errors.append("access_right must be a string")
            return errors
        
        if access_right not in self.VALID_ACCESS_RIGHTS:
            errors.append(f"Invalid access_right '{access_right}'. "
                         f"Must be one of: {', '.join(sorted(self.VALID_ACCESS_RIGHTS))}")
        
        return errors
    
    def _validate_keywords(self, keywords: Any) -> List[str]:
        """Validate keywords field"""
        errors = []
        if keywords is None:
            return errors  # Optional field
        
        if not isinstance(keywords, list):
            errors.append("Keywords must be a list")
            return errors
        
        for i, keyword in enumerate(keywords):
            if not isinstance(keyword, str):
                errors.append(f"Keyword {i+1} must be a string")
            elif not keyword.strip():
                errors.append(f"Keyword {i+1} cannot be empty")
        
        return errors
    
    def _validate_communities(self, communities: Any) -> List[str]:
        """Validate communities field"""
        errors = []
        if communities is None:
            return errors  # Optional field
        
        if not isinstance(communities, list):
            errors.append("Communities must be a list")
            return errors
        
        for i, community in enumerate(communities):
            if not isinstance(community, dict):
                errors.append(f"Community {i+1} must be a dictionary")
                continue
            
            if 'identifier' not in community:
                errors.append(f"Community {i+1} missing 'identifier' field")
            elif not community['identifier'].strip():
                errors.append(f"Community {i+1} identifier cannot be empty")
        
        return errors
    
    def _validate_publication_date(self, pub_date: Any) -> List[str]:
        """Validate publication_date field"""
        errors = []
        if pub_date is None:
            return errors  # Optional field
        
        if not isinstance(pub_date, str):
            errors.append("Publication date must be a string")
            return errors
        
        # Check date format (YYYY-MM-DD)
        try:
            datetime.strptime(pub_date, '%Y-%m-%d')
        except ValueError:
            errors.append(f"Invalid publication date format '{pub_date}'. "
                         "Expected format: YYYY-MM-DD")
        
        return errors
    
    def _is_valid_orcid(self, orcid: str) -> bool:
        """Check if ORCID format is valid"""
        # ORCID format: 0000-0000-0000-0000 (where last digit can be X)
        pattern = r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$'
        return bool(re.match(pattern, orcid))
    
    def get_validation_summary(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a summary of metadata validation status
        
        Args:
            metadata: Metadata to analyze
            
        Returns:
            Dictionary with validation summary
        """
        is_valid, errors = self.validate(metadata)
        
        return {
            'valid': is_valid,
            'error_count': len(errors),
            'errors': errors,
            'has_required_fields': all(
                field in metadata for field in self.REQUIRED_FIELDS
            ),
            'creator_count': len(metadata.get('creators', [])),
            'keyword_count': len(metadata.get('keywords', [])),
            'community_count': len(metadata.get('communities', [])),
            'estimated_quality': self._estimate_quality(metadata)
        }
    
    def _estimate_quality(self, metadata: Dict[str, Any]) -> str:
        """Estimate metadata quality based on completeness"""
        score = 0
        max_score = 10
        
        # Required fields (4 points)
        for field in self.REQUIRED_FIELDS:
            if field in metadata and metadata[field]:
                score += 1
        
        # Optional but valuable fields (6 points)
        optional_fields = [
            'keywords', 'communities', 'license', 'access_right',
            'publication_date', 'notes'
        ]
        
        for field in optional_fields:
            if field in metadata and metadata[field]:
                score += 1
                if score >= max_score:
                    break
        
        # Quality assessment
        if score >= 9:
            return "Excellent"
        elif score >= 7:
            return "Good"
        elif score >= 5:
            return "Fair"
        else:
            return "Poor"