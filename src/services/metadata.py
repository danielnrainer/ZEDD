"""
Metadata handling for Zenodo uploads
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class Funding:
    funder: str
    award_number: str
    award_title: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Zenodo API format"""
        if not self.award_title:
            return {"id": self.award_number}
        return {
            "funder": self.funder,
            "award": {"title": self.award_title, "number": self.award_number}
        }

@dataclass
class Author:
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
        """Generate HTML table directly from parameters"""
        if not self.parameters:
            return ""
            
        table_lines = [
            '<p>The table below summarizes the data collection parameters:</p>',
            '<table border="1" style="border-collapse: collapse; width: 100%;">',
            '<thead>',
            '<tr><th style="padding: 8px; background-color: #f2f2f2;">Parameter</th>',
            '<th style="padding: 8px; background-color: #f2f2f2;">Value</th></tr>',
            '</thead>',
            '<tbody>'
        ]
        
        # Add rows for each parameter that has a value
        for key, value in self.parameters.items():
            if value:  # Only include non-empty values
                table_lines.append(
                    f'<tr><td style="padding: 8px;">{key}</td>'
                    f'<td style="padding: 8px;">{value}</td></tr>'
                )
        
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
                lines.append(f"| {key} | {value} |")
        
        return '\n'.join(lines)

@dataclass
class ZenodoMetadata:
    title: str
    description: str
    creators: List[Author]
    upload_type: str = "dataset"
    access_right: str = "open"
    license: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    communities: List[Dict[str, str]] = field(default_factory=lambda: [{"identifier": "microed"}])
    publication_date: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d'))
    notes: Optional[str] = None
    ed_parameters: Optional[EDParameters] = None
    funding: List[Funding] = field(default_factory=list)
    
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
        
        # Add funding information
        if self.funding:
            metadata['grants'] = [grant.to_dict() for grant in self.funding]
        
        return metadata
