# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller spec file for ZEDD GUI
Usage: pyinstaller zedd.spec

Cross-platform Configuration:
- User config stored in OS-appropriate directories:
  * Windows: %APPDATA%/ZEDD/
  * macOS: ~/Library/Application Support/ZEDD/
  * Linux: ~/.config/ZEDD/
- Config files (settings.json, tokens.json) are NOT bundled with executable
- Only template files are bundled for defaults

Build Notes:
- This spec file works on Windows, macOS, and Linux
- On macOS, produces .app bundle
- On Linux, produces standalone executable
- User config directory is automatically created on first run
"""

import os
from pathlib import Path

block_cipher = None

# Define paths
app_name = 'ZEDD'
main_script = 'zedd_gui.py'
project_root = Path('.')

# Data files to include
datas = [
    # Include templates in the templates directory
    ('templates/app_config.json', 'templates'),
    ('templates/parameter_template.json', 'templates'),
    ('templates/cif_mappings.json', 'templates'),
    ('templates/3DED_Southampton.json', 'templates'),
    ('templates/tokens_example.json', 'templates'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtWidgets', 
    'PyQt6.QtGui',
    'PyQt6.QtWebEngineWidgets',
    'requests',
    'json',
    'pathlib',
    'dataclasses',
    'typing',
    'urllib.parse',
    # Application modules
    'src.gui.app',
    'src.gui.widgets',
    'src.gui.upload_worker',
    'src.gui.template_loader',
    'src.gui.measurement_params',
    'src.gui.multi_column_params',
    'src.services.metadata',
    'src.services.upload',
    'src.services.validation',
    'src.services.metadata_validation',
    'src.services.settings',  # Legacy module kept for interface compliance
    'src.services.user_config',  # NEW: User configuration management
    'src.services.factory',
    'src.services.templates',
    'src.services.file_packing',
    'src.services.cif_parser',
    'src.api.zenodo_api',
    'src.core.interfaces',
    'src.cli',
]

a = Analysis(
    [main_script],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary packages to reduce size
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon='icon.ico' if you have an icon file
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_name,
)

# Optional: Create a one-file executable instead
# Uncomment the following to create a single executable file:
# """
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon='icon.ico' if you have an icon file
)
# """
