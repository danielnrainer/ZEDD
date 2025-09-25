"""
Metadata handling for Zenodo uploads
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from .metadata_validation import validate_funder_api, validate_community_api

# Comprehensive list of major funders with DOI prefixes
# Combines key research funders with extensive list from Zenodo API
COMPREHENSIVE_FUNDERS = {
    "Academy of Finland": "10.13039/501100002341",
    "Agence Nationale de la Recherche": "10.13039/501100001665",
    "Aligning Science Across Parkinson’s": "10.13039/100018231",
    "Australian Research Council": "10.13039/501100000923",
    "Austrian Science Fund": "10.13039/501100002428",
    "Biotechnology and Biological Sciences Research Council": "10.13039/501100000268",
    "Canadian Institutes of Health Research": "10.13039/501100000024",
    "Deutsche Forschungsgemeinschaft": "10.13039/501100001659",
    "Engineering and Physical Sciences Research Council": "10.13039/501100000266",
    "European Commission": "10.13039/501100000780",
    "European Environment Agency": "10.13039/501100000806",
    "Fundação para a Ciência e a Tecnologia": "10.13039/501100001871",
    "Hrvatska Zaklada za Znanost": "10.13039/501100004488",
    "Innovate UK": "10.13039/501100006041",
    "Institut National Du Cancer": "10.13039/501100006364",
    "Medical Research Council": "10.13039/501100000265",
    "Ministarstvo Prosvete, Nauke i Tehnološkog Razvoja": "10.13039/501100",
    "Ministarstvo Znanosti, Obrazovanja i Sporta": "10.13039/501100006588",
    "National Health and Medical Research Council": "10.13039/501100000925",
    "National Institutes of Health": "10.13039/100000002",
    "National Science Foundation": "10.13039/100000001",
    "Natural Environment Research Council": "10.13039/501100000270",
    "Natural Sciences and Engineering Research Council of Canada": "10.13039/501100000038",
    "Nederlandse Organisatie voor Wetenschappelijk Onderzoek": "10.13039/501100003246",
    "Research Councils": "10.13039/501100000690",
    "Schweizerischer Nationalfonds zur Förderung der wissenschaftlichen Forschung": "10.13039/501100001711",
    "Science and Technology Facilities Council": "10.13039/501100000271",
    "Science Foundation Ireland": "10.13039/501100001602",
    "Social Science Research Council": "10.13039/100001345",
    "Templeton World Charity Foundation": "10.13039/501100011730",
    "Türkiye Bilimsel ve Teknolojik Araştırma Kurumu": "10.13039/501100004410",
    "UK Research and Innovation": "10.13039/100014013",
    "Wellcome Trust": "10.13039/100004440",
}

@dataclass
class Funding:
    funder: str  # Funder name or DOI prefix (e.g., "European Commission", "10.13039/501100000780")
    award_number: str  # Grant/award number
    award_title: Optional[str] = None
    url: Optional[str] = None  # URL to grant information
    _validated_doi: Optional[str] = None  # Cached DOI from API validation
    
    def validate(self, sandbox: bool = False) -> bool:
        """
        Validate the funder against curated list or API
        
        Args:
            sandbox: If True, use sandbox API for validation
            
        Returns:
            True if funder is valid (in curated list or found via API)
        """
        # Check if funder looks like a DOI prefix
        if self.funder.startswith("10.13039/"):
            return True  # Assume DOI prefixes are valid
        
        # Check if it's in the curated list
        if self.funder in COMPREHENSIVE_FUNDERS:
            return True
        
        # Try API validation
        doi_prefix = validate_funder_api(self.funder, sandbox)
        if doi_prefix:
            self._validated_doi = doi_prefix
            return True
            
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Zenodo API format
        
        Zenodo expects grants in format: {"id": "grant_id"}
        where grant_id can be:
        - Just the award number: "283595"
        - Or with DOI prefix: "10.13039/501100000780::283595"
        """
        # Check if funder looks like a DOI prefix
        if self.funder.startswith("10.13039/"):
            # Use DOI prefix format: "DOI_PREFIX::AWARD_NUMBER"
            grant_id = f"{self.funder}::{self.award_number}"
        else:
            # Check if it's a known funder name we can convert to DOI prefix
            doi_prefix = COMPREHENSIVE_FUNDERS.get(self.funder)
            if doi_prefix:
                grant_id = f"{doi_prefix}::{self.award_number}"
            elif self._validated_doi:
                # Use DOI from API validation
                grant_id = f"{self._validated_doi}::{self.award_number}"
            else:
                # For unknown funders, use just the award number
                # (Zenodo will try to match the funder name)
                grant_id = self.award_number
                
        return {"id": grant_id}
    
    @classmethod
    def get_common_funders(cls) -> List[str]:
        """Get list of common funder names for autocomplete"""
        return list(COMPREHENSIVE_FUNDERS.keys())

@dataclass
class Creator:
    name: str
    affiliation: Optional[str] = None
    orcid: Optional[str] = None
    
    def to_dict(self) -> Dict[str, str]:
        data = {"name": self.name}
        if self.affiliation:
            data["affiliation"] = self.affiliation
        if self.orcid:
            data["orcid"] = self.orcid
        return data

@dataclass
class Contributor:
    """Contributor class - for future use when contributors API is implemented
    Note: Currently commented out in GUI as Zenodo contributors API requires additional setup"""
    name: str
    affiliation: Optional[str] = None
    orcid: Optional[str] = None
    type: Optional[str] = None  # Contributor type (e.g., "researcher", "editor", "contributor")
    
    def to_dict(self) -> Dict[str, str]:
        data = {"name": self.name}
        if self.affiliation:
            data["affiliation"] = self.affiliation
        if self.orcid:
            data["orcid"] = self.orcid
        if self.type:
            data["type"] = self.type
        return data

@dataclass
class EDParameters:
    """Electron Diffraction specific parameters - now supports dynamic parameters"""
    parameters: Optional[Dict[str, str]] = field(default_factory=dict)
    
    # Backward compatibility properties
    @property
    def instrument(self) -> str:
        return self.parameters.get("Instrument", "")
    
    @property
    def detector(self) -> str:
        return self.parameters.get("Detector", "")
    
    @property
    def collection_mode(self) -> str:
        return self.parameters.get("Collection Mode", "")
    
    @property
    def voltage(self) -> str:
        return self.parameters.get("Voltage", "")
    
    @property
    def wavelength(self) -> str:
        return self.parameters.get("Wavelength", "")
    
    @property
    def exposure_time(self) -> str:
        return self.parameters.get("Exposure Time", "")
    
    @property
    def rotation_range(self) -> str:
        return self.parameters.get("Rotation Range", "")
    
    @property
    def temperature(self) -> str:
        return self.parameters.get("Temperature", "")
    
    @property
    def crystal_size(self) -> str:
        return self.parameters.get("Crystal Size", "")
    
    @property
    def sample_composition(self) -> str:
        return self.parameters.get("Sample Composition", "")
    
    def to_text(self, table_format: Optional[Dict[str, Any]] = None, format_type: str = "html") -> str:
        """
        Convert parameters to formatted text using specified or default table format
        
        Args:
            table_format: Custom table format specification  
            format_type: Output format - "html" (default) or "markdown"
        """
        # Check if any parameter has a value
        if not self.parameters or not any(v for v in self.parameters.values() if v):
            return ""

        # Use direct HTML table generation for simplicity with dynamic parameters
        if format_type.lower() == "html":
            return self._generate_html_table()
        else:
            return self._generate_markdown_table()
    
    def _generate_html_table(self) -> str:
        """Generate HTML table directly from parameters with section support (no header row)"""
        if not self.parameters:
            return ""
        
        # Get parameters organized by sections from smart section assignment
        from ..gui.template_loader import _get_smart_section
        
        # Organize parameters by sections
        sections = {}
        for key, value in self.parameters.items():
            if value:  # Only include non-empty values
                section = _get_smart_section(key)
                if section not in sections:
                    sections[section] = []
                sections[section].append((key, value))
        
        if not sections:
            return ""
            
        table_lines = [
            '<p>The table below summarizes the data collection parameters:</p>',
            '<table border="1" style="border-collapse: collapse; width: 100%;">',
            '<tbody>'
        ]
        
        # Sort sections for consistent ordering (put "General" last)
        section_order = ["General", "Instrumental", "Experimental", "Sample description", "Software & Files", "Other"]
        ordered_sections = []
        for section in section_order:
            if section in sections:
                ordered_sections.append(section)
        # Add any remaining sections not in the predefined order (like "General")
        for section in sections:
            if section not in ordered_sections:
                ordered_sections.append(section)
        
        first_section = True
        for section_name in ordered_sections:
            if section_name not in sections:
                continue
                
            # Add empty row for spacing between sections (except before first section)
            if not first_section:
                table_lines.append('<tr><td style="padding: 8px; border: none;">&nbsp;</td><td style="padding: 8px; border: none;">&nbsp;</td></tr>')
            
            # Add section header with stronger bold styling
            table_lines.append(f'<tr><td colspan="2" style="padding: 8px; font-weight: bold; background-color: #e0e0e0; font-size: 14px;"><strong><b>{section_name}</b></strong></td></tr>')
            
            # Add parameters in this section
            for key, value in sections[section_name]:
                # Convert newlines to HTML breaks for multiline entries
                formatted_value = value.replace('\n', '<br>') if '\n' in value else value
                table_lines.append(
                    f'<tr><td style="padding: 8px;">{key}</td>'
                    f'<td style="padding: 8px;">{formatted_value}</td></tr>'
                )
                
            first_section = False
        
        table_lines.extend(['</tbody>', '</table>'])
        return '\n'.join(table_lines)
    
    def _generate_markdown_table(self) -> str:
        """Generate markdown table from parameters"""
        if not self.parameters:
            return ""
            
        lines = [
            "The table below summarizes the data collection parameters:",
            "",
            "| Parameter | Value |",
            "|-----------|-------|"
        ]
        
        # Add rows for each parameter that has a value
        for key, value in self.parameters.items():
            if value:  # Only include non-empty values
                # Handle multiline values in markdown
                formatted_value = value.replace('\n', '<br>') if '\n' in value else value
                lines.append(f"| {key} | {formatted_value} |")
        
        return '\n'.join(lines)

@dataclass
class ZenodoMetadata:
    title: str
    description: str
    creators: List[Creator]
    upload_type: str = "dataset"
    access_right: str = "open"
    license: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    communities: List[Dict[str, str]] = field(default_factory=lambda: [{"identifier": "microed"}])
    publication_date: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d'))
    notes: Optional[str] = None
    contributors: List[Contributor] = field(default_factory=list)
    ed_parameters: Optional[EDParameters] = None
    funding: List[Funding] = field(default_factory=list)
    
    def validate_metadata(self, sandbox: bool = False) -> Dict[str, List[str]]:
        """
        Validate metadata including funders and communities
        
        Args:
            sandbox: If True, use sandbox mode (skip community validation)
            
        Returns:
            Dictionary with validation errors, empty if all valid
            Format: {"funders": ["error1", "error2"], "communities": ["error1"]}
        """
        errors = {"funders": [], "communities": []}
        
        # Validate funders
        for funding in self.funding:
            if not funding.validate(sandbox):
                errors["funders"].append(f"Funder '{funding.funder}' not found in curated list or Zenodo API")
        
        # Validate communities (skip in sandbox mode)
        if not sandbox:
            for community in self.communities:
                community_id = community.get("identifier")
                if community_id and not validate_community_api(community_id, sandbox):
                    errors["communities"].append(f"Community '{community_id}' not found on Zenodo")
        
        return errors
    
    def is_valid(self, sandbox: bool = False) -> bool:
        """
        Check if metadata is valid for deposition
        
        Args:
            sandbox: If True, use sandbox mode
            
        Returns:
            True if all validation passes
        """
        errors = self.validate_metadata(sandbox)
        return not any(errors.values())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to Zenodo API format"""
        metadata = {
            'title': self.title,
            'description': self.description,
            'upload_type': self.upload_type,
            'access_right': self.access_right,
            'publication_date': self.publication_date,
            'creators': [creator.to_dict() for creator in self.creators],
            'communities': self.communities
        }
        
        if self.license:
            metadata['license'] = self.license
        
        if self.keywords:
            metadata['keywords'] = self.keywords
        
        if self.notes:
            metadata['notes'] = self.notes
        
        # Add ED parameters to description if available
        if self.ed_parameters:
            ed_info = self.ed_parameters.to_text(format_type="html")
            if ed_info:
                metadata['description'] = f"{metadata['description']}\n\n{ed_info}"
        
        # Add funding information - DISABLED: Zenodo API has issues with funding
        # TODO: Users need to add funding information manually on Zenodo
        # if self.funding:
        #     metadata['grants'] = [grant.to_dict() for grant in self.funding]
        
        # Add contributors information
        if self.contributors:
            metadata['contributors'] = [contributor.to_dict() for contributor in self.contributors]
        
        return metadata
