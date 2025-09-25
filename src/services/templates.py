"""
Template data structures and management

This module provides clean data structures for handling metadata templates
without GUI dependencies.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path
import json


@dataclass
class TemplateCreator:
    """Creator data for templates (creators only - no type field)"""
    name: str = ""
    affiliation: str = ""
    orcid: str = ""


@dataclass
class TemplateContributor:
    """Contributor data for templates (future use - currently inactive)
    Note: Contributors API requires additional Zenodo setup"""
    name: str = ""
    affiliation: str = ""
    orcid: str = ""
    type: str = ""


@dataclass
class TemplateFunding:
    """Funding data for templates"""
    funder: str = ""
    award_number: str = ""
    award_title: str = ""
    url: str = ""


@dataclass
class TemplateCommunity:
    """Community data for templates"""
    identifier: str = ""


@dataclass
class TemplateEDParameters:
    """Measurement parameters for templates - now dynamic"""
    # Store as a simple dictionary to allow any number of parameters
    parameters: Dict[str, str] = field(default_factory=dict)
    
    # Legacy properties for backward compatibility
    @property
    def instrument(self) -> str:
        return self.parameters.get("Instrument", "")
    
    @instrument.setter
    def instrument(self, value: str):
        self.parameters["Instrument"] = value
    
    @property
    def detector(self) -> str:
        return self.parameters.get("Detector", "")
    
    @detector.setter
    def detector(self, value: str):
        self.parameters["Detector"] = value
    
    @property
    def collection_mode(self) -> str:
        return self.parameters.get("Collection Mode", "")
    
    @collection_mode.setter
    def collection_mode(self, value: str):
        self.parameters["Collection Mode"] = value
    
    @property
    def voltage(self) -> str:
        return self.parameters.get("Accelerating Voltage", "")
    
    @voltage.setter
    def voltage(self, value: str):
        self.parameters["Accelerating Voltage"] = value
    
    @property
    def wavelength(self) -> str:
        return self.parameters.get("Wavelength", "")
    
    @wavelength.setter
    def wavelength(self, value: str):
        self.parameters["Wavelength"] = value
    
    @property
    def exposure_time(self) -> str:
        return self.parameters.get("Exposure Time", "")
    
    @exposure_time.setter
    def exposure_time(self, value: str):
        self.parameters["Exposure Time"] = value
    
    @property
    def rotation_range(self) -> str:
        return self.parameters.get("Rotation Range", "")
    
    @rotation_range.setter
    def rotation_range(self, value: str):
        self.parameters["Rotation Range"] = value
    
    @property
    def temperature(self) -> str:
        return self.parameters.get("Temperature", "")
    
    @temperature.setter
    def temperature(self, value: str):
        self.parameters["Temperature"] = value
    
    @property
    def crystal_size(self) -> str:
        return self.parameters.get("Crystal Size", "")
    
    @crystal_size.setter
    def crystal_size(self, value: str):
        self.parameters["Crystal Size"] = value
    
    @property
    def sample_composition(self) -> str:
        return self.parameters.get("Sample Composition", "")
    
    @sample_composition.setter
    def sample_composition(self, value: str):
        self.parameters["Sample Composition"] = value


@dataclass
class MetadataTemplate:
    """Complete metadata template structure"""
    title: str = ""
    description: str = ""
    upload_type: str = "dataset"
    access_right: str = "open"
    license: str = "cc-by-4.0"
    keywords: List[str] = field(default_factory=list)
    notes: str = ""
    publication_date: str = ""
    
    # Complex objects
    creators: List[TemplateCreator] = field(default_factory=list)
    contributors: List[TemplateContributor] = field(default_factory=list)
    grants: List[TemplateFunding] = field(default_factory=list)
    communities: List[TemplateCommunity] = field(default_factory=list)
    ed_parameters: TemplateEDParameters = field(default_factory=TemplateEDParameters)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetadataTemplate':
        """Create template from dictionary"""
        # Extract and convert nested objects
        creators = [TemplateCreator(**creator) for creator in data.get('creators', [])]
        contributors = [TemplateContributor(**contributor) for contributor in data.get('contributors', [])]
        
        grants = []
        for grant_data in data.get('grants', []):
            if isinstance(grant_data, dict):
                # Handle both old and new format
                if 'award' in grant_data and isinstance(grant_data['award'], dict):
                    grants.append(TemplateFunding(
                        funder=grant_data.get('funder', ''),
                        award_number=grant_data['award'].get('number', ''),
                        award_title=grant_data['award'].get('title', ''),
                        url=grant_data.get('url', '')
                    ))
                else:
                    grants.append(TemplateFunding(**grant_data))
        
        communities = [TemplateCommunity(**comm) for comm in data.get('communities', [])]
        
        # Handle both old format (individual fields) and new format (parameters dict)
        ed_params_data = data.get('ed_parameters', {})
        if isinstance(ed_params_data, dict):
            if 'parameters' in ed_params_data:
                # New format
                ed_parameters = TemplateEDParameters(parameters=ed_params_data['parameters'])
            else:
                # Old format - convert to new format
                parameters = {}
                field_mapping = {
                    'instrument': 'Instrument',
                    'detector': 'Detector',
                    'collection_mode': 'Collection Mode',
                    'voltage': 'Accelerating Voltage',
                    'wavelength': 'Wavelength',
                    'exposure_time': 'Exposure Time',
                    'rotation_range': 'Rotation Range',
                    'temperature': 'Temperature',
                    'crystal_size': 'Crystal Size',
                    'sample_composition': 'Sample Composition'
                }
                
                for old_field, new_field in field_mapping.items():
                    if old_field in ed_params_data and ed_params_data[old_field]:
                        parameters[new_field] = ed_params_data[old_field]
                
                ed_parameters = TemplateEDParameters(parameters=parameters)
        else:
            ed_parameters = TemplateEDParameters()
        
        
        # Create main template with basic fields
        template = cls(
            title=data.get('title', ''),
            description=data.get('description', ''),
            upload_type=data.get('upload_type', 'dataset'),
            access_right=data.get('access_right', 'open'),
            license=data.get('license', 'cc-by-4.0'),
            keywords=data.get('keywords', []),
            notes=data.get('notes', ''),
            publication_date=data.get('publication_date', ''),
            creators=creators,
            contributors=contributors,
            grants=grants,
            communities=communities,
            ed_parameters=ed_parameters
        )
        
        return template


class TemplateService:
    """Service for loading and saving metadata templates"""
    
    def __init__(self, templates_dir: Path = None):
        """Initialize template service"""
        if templates_dir is None:
            # Default to templates/ directory relative to this file
            templates_dir = Path(__file__).parent.parent.parent / "templates"
        self.templates_dir = templates_dir
    
    def load_template(self, filename: str) -> MetadataTemplate:
        """Load template from file"""
        file_path = self.templates_dir / filename
        
        if not file_path.exists():
            # Return default template if file doesn't exist
            return MetadataTemplate()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return MetadataTemplate.from_dict(data)
        except Exception as e:
            print(f"Failed to load template {filename}: {e}")
            return MetadataTemplate()
    
    def save_template(self, template: MetadataTemplate, filename: str) -> bool:
        """Save template to file"""
        try:
            self.templates_dir.mkdir(exist_ok=True)
            file_path = self.templates_dir / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(template.to_dict(), f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Failed to save template {filename}: {e}")
            return False
    
    def load_user_template(self, file_path: str) -> MetadataTemplate:
        """Load template from arbitrary file path"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return MetadataTemplate.from_dict(data)
        except Exception as e:
            print(f"Failed to load template from {file_path}: {e}")
            return MetadataTemplate()
    
    def get_default_template(self) -> MetadataTemplate:
        """Get default template with sensible defaults"""
        template = MetadataTemplate()
        template.creators = [TemplateCreator()]  # One empty creator
        template.communities = [TemplateCommunity(identifier="microed")]  # Default community
        return template