# Zenodo Uploader for Electron Diffraction Data

A Python application for uploading electron diffraction datasets to Zenodo with specialized metadata support. Provides both graphical and command-line interfaces.

_Disclaimer_
The code in this project has been written in large parts by LLM models (mainly Anthropic's Sonnet 4.5 and Opus 4.5).

Be advised that this software is in constant development and might therefore contain bugs or other unintended behaviour. Always check your Zenodo entries carefully before publishing and if you encounter an issue and would like to report it, please do so via the [Issues](https://github.com/danielnrainer/ZEDD/issues) section.

## ✨ Features

- **User-friendly GUI** with collapsible sections, drag-and-drop file support, and real-time validation
- **Dynamic metadata management** including authors, funding, communities, and custom experimental parameters
- **CIF import support** - automatically populate table parameters from one or more CIF (Crystallographic Information File) files
- **Multi-column parameter tables** - document multiple crystal structures with one column per CIF file
- **HTML table generation** for structured parameter display in Zenodo descriptions
- **Command-line interface** for automated workflows
- **Template system** for consistent metadata across research groups
- **Progress tracking** and error handling during uploads
- **Sandbox mode** for testing before publishing

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PyQt6 for GUI functionality

### Installation

```bash
# Clone the repository
git clone https://github.com/danielnrainer/ZEDD.git
cd ZEDD

# Install dependencies
pip install -r requirements.txt
```

### Usage

**GUI Interface:**
```bash
python zedd_gui.py
```

**Command Line:**
```bash
# Using metadata file
python -m src.cli -z YOUR_ZENODO_TOKEN -m metadata.json -f data_folder.zip --sandbox

# Direct options
python -m src.cli -z YOUR_TOKEN -T "Dataset Title" -C "Last, First" -A "Institution" -f data_folder
```

## 📋 Metadata Example

```json
{
    "title": "Electron Diffraction Dataset",
    "description": "Description of the dataset...",
    "creators": [
        {
            "name": "Last, First",
            "affiliation": "Institution",
            "orcid": "0000-0000-0000-0000"
        }
    ],
    "keywords": ["electron diffraction", "crystallography"],
    "upload_type": "dataset",
    "access_right": "open",
    "license": "cc-by-4.0",
    "communities": [{"identifier": "microed"}],
    "ed_parameters": {
        "instrument": "Rigaku XtaLAB Synergy-ED",
        "detector": "Hybrid Electron Detector",
        "voltage": "200 kV",
        "wavelength": "0.0251 Å",
        "temperature": "175 K"
    }
}
```

## 🔧 Configuration

### User Data Directory

ZEDD stores all user configuration in a platform-specific application data directory:

| Platform | Location |
|----------|----------|
| Windows  | `%APPDATA%\ZEDD\` |
| macOS    | `~/Library/Application Support/ZEDD/` |
| Linux    | `~/.config/ZEDD/` |

**Configuration Files:**
```
ZEDD/
├── settings.json           # GUI state, last values, preferences
├── tokens.json             # API tokens (sandbox & production)
├── user_template.json      # Custom metadata template (optional)
└── cif_mappings.json       # Custom CIF mappings (optional)
```

**Customization:**
- **`tokens.json`**: Store your Zenodo API tokens (both sandbox and production)
- **`user_template.json`**: Create your own default metadata template (overrides bundled templates)
- **`cif_mappings.json`**: Customize CIF data name mappings (extends/overrides bundled mappings)
- All files use JSON format for easy editing

Settings persist across sessions and software updates.

### Bundled Template Files

The application includes default templates in the `templates/` directory:
- `app_config.json` - Application configuration
- `cif_mappings.json` - Default CIF data name mappings (supports CIF1 and CIF2)
- `parameter_template.json` - Default parameter template
- `3DED_Southampton.json` - Example 3D electron diffraction template

User config files (if present) take precedence over bundled templates.

### Example User Config Files

**`tokens.json` Example:**
```json
{
  "sandbox": "your-sandbox-token-here",
  "production": "your-production-token-here"
}
```

Store your Zenodo API tokens here to avoid entering them manually. The app automatically loads the appropriate token based on the sandbox checkbox. Access via **File → Open Config Directory** in the app.

**`user_template.json` Example:**
```json
{
  "title": "My Default Dataset",
  "description": "Standard dataset from my lab",
  "upload_type": "dataset",
  "access_right": "open",
  "creators": [
    {
      "name": "Smith, John",
      "affiliation": "My University",
      "orcid": "0000-0000-0000-0000"
    }
  ],
  "keywords": ["electron diffraction", "crystallography"],
  "notes": "Data collected using standard protocols"
}
```

**`cif_mappings.json` Example:**
```json
{
  "_custom_instrument_name": ["Instrument", "Instrumental"],
  "_custom_detector_type": ["Detector", "Instrumental"],
  "_my_lab_wavelength": ["Wavelength (Å)", "Instrumental"]
}
```

Each entry maps a CIF data name to `[Display Name, Section]` where Section is one of: "General", "Instrumental", "Sample", "Experimental", or "Software".

## 📁 CIF Import Feature

The application can automatically populate experimental parameters from CIF (Crystallographic Information File) files. This is especially useful when your data is associated with one or more crystal structures.

### How to Use

1. In the GUI, navigate to the **Experimental Parameters** section
2. Click the **"📂 Import from CIF..."** button
3. Select one or more CIF files
4. Parameters will be extracted and added as new columns in the table

### Supported CIF Data Names

CIF data name mappings are configured in `templates/cif_mappings.json`. Both modern (dot notation, e.g., `_cell.length_a`) and legacy (underscore notation, e.g., `_cell_length_a`) CIF formats are supported.

Key mappings include:

| Category | CIF Data Name | Table Parameter |
|----------|---------------|-----------------|
| **Instrumental** | `_diffrn_source.make` | Instrument |
| | `_diffrn_radiation_wavelength.value` | Wavelength [Å] |
| | `_diffrn_source.voltage` | Accelerating voltage [kV] |
| | `_diffrn_detector.detector` | Detector |
| **Sample** | `_chemical.name_common` | Name |
| | `_chemical_formula.sum` | Chemical composition |
| | `_exptl_crystal.preparation` | Sample preparation |
| **Experimental** | `_diffrn.ambient_temperature` | Temperature [K] |
| | `_space_group.name_h-m_alt` | Space group |
| | `_cell.length_a/b/c` | Unit cell dimensions |
| **Software** | `_computing.data_collection` | Software for data collection |
| | `_computing.data_reduction` | Software for data processing |

Over 100 CIF data names are supported - see `templates/cif_mappings.json` for the complete mapping. Edit this file to customize mappings for your needs.

### Multiple CIF Files

When you import multiple CIF files, each file creates a new column in the parameter table. This allows you to document all crystal structures from your deposition in a single organized table.
