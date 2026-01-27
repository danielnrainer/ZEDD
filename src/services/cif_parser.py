"""
CIF (Crystallographic Information File) parser for extracting metadata.

This module parses CIF files and extracts data name/value pairs that can be
mapped to Zenodo deposition metadata fields.

The CIF data name mappings are loaded from templates/cif_mappings.json for
easy customization without modifying Python code.
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =========================================================================
# CIF MAPPING CONFIGURATION LOADER
# =========================================================================

def _get_templates_dir() -> Path:
    """Get the templates directory path"""
    # Try relative to this file first
    this_file = Path(__file__).resolve()
    templates_dir = this_file.parent.parent.parent / "templates"
    if templates_dir.exists():
        return templates_dir
    
    # Fallback: try current working directory
    cwd_templates = Path.cwd() / "templates"
    if cwd_templates.exists():
        return cwd_templates
    
    raise FileNotFoundError("Could not locate templates directory")


def _load_cif_mappings() -> Tuple[Dict[str, Tuple[str, str]], Dict[str, str]]:
    """
    Load CIF data name mappings from the JSON configuration file.
    
    Returns:
        Tuple of (parameter_mapping, legacy_aliases)
        - parameter_mapping: {cif_tag: (display_name, section)}
        - legacy_aliases: {legacy_tag: modern_tag}
    """
    try:
        templates_dir = _get_templates_dir()
        config_file = templates_dir / "cif_mappings.json"
        
        if not config_file.exists():
            logger.warning(f"CIF mappings file not found: {config_file}")
            return {}, {}
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Flatten parameter_mapping from categorized structure
        parameter_mapping = {}
        for category, mappings in config.get("parameter_mapping", {}).items():
            if category.startswith("_"):  # Skip comment fields
                continue
            if isinstance(mappings, dict):
                for cif_tag, (display_name, section) in mappings.items():
                    if not cif_tag.startswith("_comment"):
                        parameter_mapping[cif_tag] = (display_name, section)
        
        # Flatten legacy_to_modern_aliases from categorized structure
        legacy_aliases = {}
        for category, aliases in config.get("legacy_to_modern_aliases", {}).items():
            if category.startswith("_"):  # Skip comment fields
                continue
            if isinstance(aliases, dict):
                for legacy, modern in aliases.items():
                    if not legacy.startswith("_comment"):
                        legacy_aliases[legacy] = modern
        
        logger.debug(f"Loaded {len(parameter_mapping)} CIF mappings and {len(legacy_aliases)} aliases")
        return parameter_mapping, legacy_aliases
        
    except Exception as e:
        logger.error(f"Error loading CIF mappings: {e}")
        return {}, {}


# Load mappings at module import time
CIF_TO_PARAMETER_MAPPING, CIF_TAG_ALIASES = _load_cif_mappings()


@dataclass
class CIFData:
    """Container for parsed CIF data"""
    filename: str
    data_block_name: str = ""
    data_items: Dict[str, str] = field(default_factory=dict)
    loop_data: Dict[str, List[Dict[str, str]]] = field(default_factory=dict)
    
    def get(self, key: str, default: str = "") -> str:
        """Get a data item value, checking common prefixes"""
        # Try exact match first
        if key in self.data_items:
            return self.data_items[key]
        
        # Try with underscore prefix
        if not key.startswith("_") and f"_{key}" in self.data_items:
            return self.data_items[f"_{key}"]
        
        return default
    
    def get_loop_items(self, category: str) -> List[Dict[str, str]]:
        """Get all items from a loop category (e.g., 'audit_author')"""
        return self.loop_data.get(category, [])


class CIFParser:
    """
    Parser for CIF (Crystallographic Information File) format.
    
    Supports CIF 1.1 format with:
    - Simple data items (_tag value)
    - Multi-line text (semicolon-delimited)
    - Loop structures
    """
    
    def __init__(self):
        # Regex patterns
        self._data_block_pattern = re.compile(r'^data_(\S+)', re.IGNORECASE)
        self._tag_pattern = re.compile(r'^(_\S+)\s+(.+)$')
        self._loop_pattern = re.compile(r'^loop_\s*$', re.IGNORECASE)
        self._tag_only_pattern = re.compile(r'^(_\S+)\s*$')
    
    def parse_file(self, filepath: str) -> CIFData:
        """
        Parse a CIF file and return structured data.
        
        Args:
            filepath: Path to the CIF file
            
        Returns:
            CIFData object containing parsed data
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"CIF file not found: {path}")
        
        # Try different encodings
        content = None
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                content = path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            raise ValueError(f"Could not decode CIF file: {path}")
        
        return self.parse_string(content, path.name)
    
    def parse_string(self, content: str, filename: str = "unknown") -> CIFData:
        """
        Parse CIF content from a string.
        
        Args:
            content: CIF file content as string
            filename: Name to associate with the data
            
        Returns:
            CIFData object containing parsed data
        """
        cif_data = CIFData(filename=filename)
        
        # Normalize line endings
        lines = content.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                i += 1
                continue
            
            # Check for data block
            match = self._data_block_pattern.match(line)
            if match:
                cif_data.data_block_name = match.group(1)
                i += 1
                continue
            
            # Check for loop
            if self._loop_pattern.match(line):
                i = self._parse_loop(lines, i, cif_data)
                continue
            
            # Check for tag-value pair on same line
            match = self._tag_pattern.match(line)
            if match:
                tag = match.group(1).lower()
                value = self._clean_value(match.group(2))
                cif_data.data_items[tag] = value
                i += 1
                continue
            
            # Check for tag only (value on next line or multiline)
            match = self._tag_only_pattern.match(line)
            if match:
                tag = match.group(1).lower()
                i += 1
                if i < len(lines):
                    next_line = lines[i].strip()
                    if next_line.startswith(';'):
                        # Multi-line value
                        value, i = self._parse_multiline(lines, i)
                        cif_data.data_items[tag] = value
                    else:
                        # Single value on next line
                        cif_data.data_items[tag] = self._clean_value(next_line)
                        i += 1
                continue
            
            # Check for multiline value starting
            if line.startswith(';'):
                # This shouldn't happen without a preceding tag, skip
                i += 1
                continue
            
            i += 1
        
        return cif_data
    
    def _parse_multiline(self, lines: List[str], start_idx: int) -> Tuple[str, int]:
        """Parse a semicolon-delimited multiline value"""
        # Skip the opening semicolon line
        i = start_idx + 1
        value_lines = []
        
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith(';') and len(line.strip()) == 1:
                # End of multiline
                i += 1
                break
            value_lines.append(line)
            i += 1
        
        return '\n'.join(value_lines).strip(), i
    
    def _parse_loop(self, lines: List[str], start_idx: int, cif_data: CIFData) -> int:
        """Parse a loop_ structure"""
        i = start_idx + 1  # Skip 'loop_' line
        tags = []
        
        # Collect tags
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith('#'):
                i += 1
                continue
            if line.startswith('_'):
                tags.append(line.lower())
                i += 1
            else:
                break
        
        if not tags:
            return i
        
        # Determine category from first tag
        category = tags[0].split('.')[0].lstrip('_') if '.' in tags[0] else tags[0].lstrip('_').rsplit('_', 1)[0]
        
        if category not in cif_data.loop_data:
            cif_data.loop_data[category] = []
        
        # Collect values
        values_buffer = []
        while i < len(lines):
            line = lines[i].strip()
            
            # Stop at new data block, loop, or tag definition
            if not line:
                i += 1
                continue
            if line.startswith('#'):
                i += 1
                continue
            if line.startswith('data_') or line.lower() == 'loop_' or (line.startswith('_') and not values_buffer):
                break
            
            # Handle multiline values in loops
            if line.startswith(';'):
                value, i = self._parse_multiline(lines, i - 1)
                values_buffer.append(value)
                continue
            
            # Parse values from line
            parsed = self._parse_loop_values(line)
            values_buffer.extend(parsed)
            i += 1
            
            # Check if we have complete rows
            while len(values_buffer) >= len(tags):
                row_values = values_buffer[:len(tags)]
                values_buffer = values_buffer[len(tags):]
                
                row_dict = {}
                for tag, value in zip(tags, row_values):
                    row_dict[tag] = value
                cif_data.loop_data[category].append(row_dict)
        
        return i
    
    def _parse_loop_values(self, line: str) -> List[str]:
        """Parse values from a loop data line, handling quoted strings"""
        values = []
        i = 0
        line = line.strip()
        
        while i < len(line):
            # Skip whitespace
            while i < len(line) and line[i] in ' \t':
                i += 1
            
            if i >= len(line):
                break
            
            # Check for quoted string
            if line[i] in '"\'':
                quote = line[i]
                i += 1
                start = i
                while i < len(line) and line[i] != quote:
                    i += 1
                values.append(line[start:i])
                i += 1  # Skip closing quote
            else:
                # Unquoted value
                start = i
                while i < len(line) and line[i] not in ' \t':
                    i += 1
                values.append(self._clean_value(line[start:i]))
        
        return values
    
    def _clean_value(self, value: str) -> str:
        """Clean a CIF value (remove quotes, handle special values)"""
        value = value.strip()
        
        # Remove surrounding quotes
        if len(value) >= 2:
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
        
        # Handle CIF special values
        if value in ('?', '.'):
            return ''
        
        return value


def extract_parameters_from_cif(cif_data: CIFData) -> Dict[str, Tuple[str, str]]:
    """
    Extract Zenodo table parameters from parsed CIF data.
    
    Args:
        cif_data: Parsed CIF data
        
    Returns:
        Dictionary mapping parameter names to (value, section) tuples
    """
    parameters = {}
    
    # Process each data item
    for cif_tag, value in cif_data.data_items.items():
        if not value:
            continue
        
        # Normalize tag (handle aliases)
        normalized_tag = CIF_TAG_ALIASES.get(cif_tag, cif_tag)
        
        # Check if we have a mapping for this tag
        if normalized_tag in CIF_TO_PARAMETER_MAPPING:
            param_name, section = CIF_TO_PARAMETER_MAPPING[normalized_tag]
            # Don't overwrite if we already have a value (first match wins)
            if param_name not in parameters:
                parameters[param_name] = (value, section)
        elif cif_tag in CIF_TO_PARAMETER_MAPPING:
            param_name, section = CIF_TO_PARAMETER_MAPPING[cif_tag]
            if param_name not in parameters:
                parameters[param_name] = (value, section)
    
    # Handle special composite parameters
    _add_crystal_size(cif_data, parameters)
    _add_unit_cell(cif_data, parameters)
    _add_authors(cif_data, parameters)
    
    return parameters


def _add_crystal_size(cif_data: CIFData, parameters: Dict[str, Tuple[str, str]]) -> None:
    """Combine crystal size dimensions into a single parameter"""
    sizes = []
    for tag in ["_exptl_crystal.size_max", "_exptl_crystal.size_mid", "_exptl_crystal.size_min"]:
        # Check both dot notation and underscore notation
        value = cif_data.get(tag) or cif_data.get(tag.replace(".", "_"))
        if value:
            sizes.append(value)
    
    if sizes:
        size_str = " × ".join(sizes)
        if "Crystal size" not in parameters:
            parameters["Crystal size [mm]"] = (size_str, "Sample description")


def _add_unit_cell(cif_data: CIFData, parameters: Dict[str, Tuple[str, str]]) -> None:
    """Format unit cell as a compact string if individual values exist"""
    # This is optional - we keep individual a, b, c values as well
    a = cif_data.get("_cell.length_a") or cif_data.get("_cell_length_a")
    b = cif_data.get("_cell.length_b") or cif_data.get("_cell_length_b")
    c = cif_data.get("_cell.length_c") or cif_data.get("_cell_length_c")
    alpha = cif_data.get("_cell.angle_alpha") or cif_data.get("_cell_angle_alpha")
    beta = cif_data.get("_cell.angle_beta") or cif_data.get("_cell_angle_beta")
    gamma = cif_data.get("_cell.angle_gamma") or cif_data.get("_cell_angle_gamma")
    
    if a and b and c:
        cell_str = f"a={a}, b={b}, c={c}"
        if alpha and beta and gamma:
            cell_str += f", α={alpha}, β={beta}, γ={gamma}"
        if "Unit cell" not in parameters:
            parameters["Unit cell"] = (cell_str, "Experimental")


def _add_authors(cif_data: CIFData, parameters: Dict[str, Tuple[str, str]]) -> None:
    """Extract author information from loop data"""
    author_items = cif_data.get_loop_items("audit_author")
    if author_items:
        authors = []
        for item in author_items:
            name = item.get("_audit_author.name", "")
            if name:
                authors.append(name)
        if authors:
            parameters["CIF Author(s)"] = ("; ".join(authors), "General")


def parse_multiple_cifs(filepaths: List[str]) -> List[Tuple[str, Dict[str, Tuple[str, str]]]]:
    """
    Parse multiple CIF files and extract parameters from each.
    
    Args:
        filepaths: List of paths to CIF files
        
    Returns:
        List of (filename, parameters_dict) tuples
    """
    parser = CIFParser()
    results = []
    
    for filepath in filepaths:
        try:
            cif_data = parser.parse_file(filepath)
            parameters = extract_parameters_from_cif(cif_data)
            results.append((cif_data.filename, parameters))
        except Exception as e:
            # Return partial results with error indication
            results.append((Path(filepath).name, {"Error": (str(e), "General")}))
    
    return results


def get_all_cif_parameters() -> List[Tuple[str, str]]:
    """
    Get a list of all possible parameters that can be extracted from CIF files.
    
    Returns:
        List of (parameter_name, section) tuples, sorted by section then name
    """
    # Get unique parameter names and their sections
    params = set()
    for cif_tag, (param_name, section) in CIF_TO_PARAMETER_MAPPING.items():
        params.add((param_name, section))
    
    # Add composite parameters
    params.add(("Crystal size [mm]", "Sample description"))
    params.add(("Unit cell", "Experimental"))
    params.add(("CIF Author(s)", "General"))
    
    # Sort by section, then by name
    section_order = ["General", "Instrumental", "Sample description", "Experimental", "Software & Files"]
    
    def sort_key(item):
        name, section = item
        try:
            section_idx = section_order.index(section)
        except ValueError:
            section_idx = len(section_order)
        return (section_idx, name.lower())
    
    return sorted(list(params), key=sort_key)
