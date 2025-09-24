# Zenodo Uploader for Electron Diffraction Data

A Python application for uploading electron diffraction datasets to Zenodo with specialized metadata support. Provides both graphical and command-line interfaces.

## ✨ Features

- **User-friendly GUI** with collapsible sections, drag-and-drop file support, and real-time validation
- **Dynamic metadata management** including authors, funding, communities, and custom experimental parameters
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
git clone https://github.com/yourusername/zenodo-uploader.git
cd zenodo-uploader
pip install -r requirements.txt
```

### Usage

**GUI Interface:**
```bash
python zenodo_uploader_gui.py
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

## 📦 Building Standalone Executable

For Windows distribution:

```bash
# Install PyInstaller (if not already installed)
pip install pyinstaller

# Build executable using the build script
build.bat

# Or manually with PyInstaller
pyinstaller zenodo_uploader.spec
```

For Linux/macOS:
```bash
# Make build script executable and run
chmod +x build.sh
./build.sh
```

The executable will be created in `dist/ZenodoUploader/` and can be distributed as a complete folder.

## 🏗️ Project Structure

```
zenodo_uploader/
├── src/
│   ├── api/                 # Zenodo API integration
│   ├── core/                # Core interfaces  
│   ├── services/            # Business logic (metadata, upload, validation)
│   ├── gui/                 # GUI components
│   └── cli.py               # Command-line interface
├── templates/               # Configuration templates
├── zenodo_uploader_gui.py   # Main GUI launcher
└── zenodo_uploader.spec     # PyInstaller build specification
```

## 🔧 Configuration

The application uses template files in the `templates/` directory:
- `app_config.json` - Application settings
- `comprehensive_template.json` - Complete metadata example

Settings are automatically saved and restored between sessions.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## 📄 License

This project is licensed under the MIT License.
