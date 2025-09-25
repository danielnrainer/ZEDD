"""
Main application window class
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QFormLayout, QGroupBox, QLineEdit, QTextEdit, QTextBrowser, QComboBox, 
    QPushButton, QFileDialog, QProgressBar, QLabel, QMessageBox,
    QTabWidget, QCheckBox, QDateEdit, QScrollArea, QCompleter
)
from PyQt6.QtCore import QSettings, QDate, Qt, QStringListModel
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import zipfile
import json

from .widgets import QCollapsibleBox, CreatorWidget, ContributorWidget
from .upload_worker import ModularUploadWorker
from .template_loader import populate_gui_from_template
from .measurement_params import MeasurementParametersWidget
from ..services import get_service_factory
from ..services.metadata import Creator, Contributor, EDParameters, ZenodoMetadata, Funding
from ..services.file_packing import create_zip_from_folder

def is_frozen_executable():
    """Check if running as a PyInstaller executable"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


class ZenodoUploaderApp(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Get the service factory
        self.service_factory = get_service_factory()
        
        # Keep original QSettings for backward compatibility with GUI
        # Use unique organization name to avoid sharing settings with development version
        self.settings = QSettings("ZEDD", "ZenodoElectronDiffractionDepositor")
        
        self.licenses = []
        # Lists to track dynamic widgets
        self.creators_list = []
        self.contributors_list = []
        self.upload_worker = None  # Track upload worker
        # Guard used to avoid re-entrant UI updates while loading metadata
        self._loading_metadata = False
        
        self.init_ui()
        self.load_settings()
        
        # Initialize services if token is available - but don't load token in executables
        if is_frozen_executable():
            # In executable mode: never initialize with saved tokens
            token = ""
            sandbox = True
        else:
            # In development mode: use saved tokens
            token = self.settings.value("api/token", "")
            sandbox = self.settings.value("api/sandbox", True, type=bool)
            
        if token:
            self.service_factory.update_api_config(token, sandbox)
            self.load_licenses()
    
    def init_ui(self):
        # Set title with indicator if running as executable
        title = "ZEDD - Zenodo Electron Diffraction Depositor"
        if is_frozen_executable():
            title += " (Portable)"
        self.setWindowTitle(title)
        self.setGeometry(100, 100, 1000, 800)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Configuration tab
        self.config_tab = self.create_config_tab()
        self.tab_widget.addTab(self.config_tab, "Configuration")
        
        # Metadata tab
        self.metadata_tab = self.create_metadata_tab()
        self.tab_widget.addTab(self.metadata_tab, "Metadata")
        
        # Upload tab
        self.upload_tab = self.create_upload_tab()
        self.tab_widget.addTab(self.upload_tab, "Upload")
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
    def closeEvent(self, event):
        """Handle application close event"""
        # Check if upload is in progress
        if hasattr(self, 'upload_worker') and self.upload_worker and self.upload_worker.isRunning():
            reply = QMessageBox.question(
                self, 
                'Upload in Progress',
                'An upload is currently in progress. Do you want to cancel it and exit?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Cancel upload and wait for it to finish
                self.status_label.setText("Cancelling upload before exit...")
                self.upload_worker.cancel()
                if not self.upload_worker.wait(5000):  # Wait up to 5 seconds
                    self.upload_worker.terminate()
                    self.upload_worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            # Save settings before closing
            self.save_settings()
            event.accept()
        
    def load_settings(self):
        """Load saved settings"""
        # Load API configuration - but don't load token in distributed executables
        if is_frozen_executable():
            # In distributed executable: don't load sensitive data like tokens
            self.token_edit.setText("")
            self.sandbox_checkbox.setChecked(True)  # Default to sandbox for safety
        else:
            # In development: load all settings normally
            self.token_edit.setText(self.settings.value("api/token", ""))
            self.sandbox_checkbox.setChecked(self.settings.value("api/sandbox", True, type=bool))
        
        # Try to load default values from templates
        # Always prioritize parameter_template.json for consistent best practices
        template_path = None
        default_values = {}
        
        # First try parameter_template.json (preferred)
        template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'templates', 'parameter_template.json')
        if not os.path.exists(template_path):
            # Fallback to default_metadata.json if parameter_template doesn't exist
            template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'templates', 'default_metadata.json')
        
        if template_path and os.path.exists(template_path):
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    default_values = json.loads(f.read())
                print(f"Loaded template for best practices: {os.path.basename(template_path)}")
            except Exception as e:
                print(f"Failed to load template metadata from {template_path}: {e}")
        
        # Always populate all fields from template for best practices and consistency
        if default_values:
            if is_frozen_executable():
                # In executable mode: always use complete template loading
                self._load_complete_template(default_values)
            else:
                # In development mode: use template but allow saved settings to override
                self._load_template_with_saved_overrides(default_values)
        else:
            # Fallback if no template available
            self._load_individual_settings({})
    
    def _load_complete_template(self, template_data: dict):
        """Load complete template data (used in executable mode)"""
        from .template_loader import populate_gui_from_template
        from ..services.templates import MetadataTemplate
        
        try:
            # Convert dictionary to MetadataTemplate object
            template = MetadataTemplate.from_dict(template_data)
            # Use the existing template loader to populate the GUI
            populate_gui_from_template(self, template)
        except Exception as e:
            print(f"Failed to load complete template: {e}")
            # Fallback to individual settings loading
            self._load_individual_settings(template_data)
    
    def _load_template_with_saved_overrides(self, template_data: dict):
        """Load template but allow saved settings to override (used in development mode)"""
        from .template_loader import populate_gui_from_template
        from ..services.templates import MetadataTemplate
        
        try:
            # First load the complete template
            template = MetadataTemplate.from_dict(template_data)
            populate_gui_from_template(self, template)
            
            # Then override with saved settings where they exist
            # Only override fields that have been explicitly saved by user
            saved_title = self.settings.value("metadata/title", "")
            if saved_title and saved_title != template_data.get("title", ""):
                self.title_edit.setText(saved_title)
                
            saved_desc = self.settings.value("metadata/description", "")
            if saved_desc and saved_desc != template_data.get("description", ""):
                self.description_edit.setPlainText(saved_desc)
                
            # Override other key fields if explicitly saved
            saved_keywords = self.settings.value("metadata/keywords", "")
            if saved_keywords and saved_keywords != template_data.get("keywords", []):
                if isinstance(saved_keywords, list):
                    self.keywords_edit.setText(", ".join(saved_keywords))
                else:
                    self.keywords_edit.setText(str(saved_keywords))
            
        except Exception as e:
            print(f"Failed to load template with overrides: {e}")
            # Fallback to individual settings loading
            self._load_individual_settings(template_data)
    
    def _load_individual_settings(self, default_values: dict):
        """Load individual saved settings or template defaults (used in development mode)"""
        # Load saved creator data or use defaults
        creators_data = self.settings.value("creators", default_values.get("creators", []))
        if creators_data:
            for creator_data in creators_data:
                if len(self.creators_list) > 0:
                    self.creators_list[0].set_data(creator_data)
                else:
                    self.add_creator()
                    self.creators_list[0].set_data(creator_data)
        
        # Load saved contributor data or use defaults
        contributors_data = self.settings.value("contributors", default_values.get("contributors", []))
        if contributors_data:
            for contributor_data in contributors_data:
                self.add_contributor()
                self.contributors_list[-1].set_data(contributor_data)
        
        # Load saved funding data - DISABLED: Zenodo API has issues with funding
        # TODO: Users need to add funding information manually on Zenodo
        # funding_data = self.settings.value("funding", default_values.get("grants", []))
        # if funding_data:
        #     for grant_data in funding_data:
        #         if isinstance(grant_data, dict):
        #             self.add_funding()
        #             widget = self.funding_list[-1]
        #             
        #             # Handle new format
        #             if "funder" in grant_data:
        #                 widget.property('funder_edit').setText(grant_data["funder"])
        #             if "award_number" in grant_data:
        #                 widget.property('award_number_edit').setText(grant_data["award_number"])
        #             if "award_title" in grant_data:
        #                 widget.property('award_title_edit').setText(grant_data["award_title"])
        #             if "url" in grant_data:
        #                 widget.property('url_edit').setText(grant_data["url"])
        #             
        #             # Handle old format for backward compatibility
        #             elif "award" in grant_data and isinstance(grant_data["award"], dict):
        #                 if "number" in grant_data["award"]:
        #                     widget.property('award_number_edit').setText(grant_data["award"]["number"])
        #                 if "title" in grant_data["award"]:
        #                     widget.property('award_title_edit').setText(grant_data["award"]["title"])
        
        # Load metadata fields from settings or defaults
        ed_params = default_values.get("ed_parameters", {})
        params_dict = {}
        
        # Handle both old and new format
        if isinstance(ed_params, dict):
            if "parameters" in ed_params:
                # New format with parameters dict
                params_dict = ed_params["parameters"]
            else:
                # Old format - direct key-value pairs (backward compatibility)
                params_dict = {k: str(v) for k, v in ed_params.items() if v is not None}
        
        # Load individual field settings or use template defaults
        self.title_edit.setText(self.settings.value("metadata/title", default_values.get("title", "")))
        self.description_edit.setPlainText(self.settings.value("metadata/description", default_values.get("description", "")))
        
        # Upload type combo
        upload_type = self.settings.value("metadata/upload_type", default_values.get("upload_type", "dataset"))
        index = self.upload_type_combo.findText(upload_type)
        if index >= 0:
            self.upload_type_combo.setCurrentIndex(index)
            
        # Access right combo  
        access_right = self.settings.value("metadata/access_right", default_values.get("access_right", "open"))
        index = self.access_right_combo.findText(access_right)
        if index >= 0:
            self.access_right_combo.setCurrentIndex(index)
        
        # Keywords
        keywords = self.settings.value("metadata/keywords", default_values.get("keywords", []))
        if keywords:
            if isinstance(keywords, list):
                self.keywords_edit.setText(", ".join(keywords))
            else:
                self.keywords_edit.setText(str(keywords))
        
        # Publication date
        pub_date_str = self.settings.value("metadata/publication_date", default_values.get("publication_date", ""))
        if pub_date_str:
            try:
                date = QDate.fromString(pub_date_str, "yyyy-MM-dd")
                if date.isValid():
                    self.publication_date_edit.setDate(date)
            except Exception:
                pass
        
        self.notes_edit.setPlainText(self.settings.value("metadata/notes", default_values.get("notes", "")))
        
        # Populate the measurement parameters widget
        self.measurement_params_widget.clear_parameters()
        for key, value in params_dict.items():
            if value:  # Only add non-empty values
                self.measurement_params_widget.add_parameter(key, value)
    
    def save_settings(self):
        """Save current settings"""
        # Don't save settings in distributed executables to avoid storing user data
        if is_frozen_executable():
            return
            
        # Save API configuration
        self.settings.setValue("api/token", self.token_edit.text())
        self.settings.setValue("api/sandbox", self.sandbox_checkbox.isChecked())
        
        # Save creator data
        creators_data = []
        for creator_widget in self.creators_list:
            creator_data = creator_widget.get_data()
            if creator_data.get("name"):
                creators_data.append(creator_data)
        self.settings.setValue("creators", creators_data)
        
        # Save contributor data
        contributors_data = []
        for contributor_widget in self.contributors_list:
            contributor_data = contributor_widget.get_data()
            if contributor_data.get("name"):
                contributors_data.append(contributor_data)
        self.settings.setValue("contributors", contributors_data)
        
        # Save measurement parameters (new dict-based format)
        params = self.measurement_params_widget.get_parameters()
        self.settings.setValue("ed/parameters", params)
        
        # Also save individual fields for backward compatibility
        param_mapping = {
            "Instrument": "instrument", "Detector": "detector", 
            "Collection Mode": "collection_mode", "Voltage": "voltage",
            "Wavelength": "wavelength", "Exposure Time": "exposure_time",
            "Rotation Range": "rotation_range", "Temperature": "temperature",
            "Crystal Size": "crystal_size", "Sample Composition": "sample_composition"
        }
        for display_key, setting_key in param_mapping.items():
            value = params.get(display_key, "")
            self.settings.setValue(f"ed/{setting_key}", value)
        
        # Save general metadata
        self.settings.setValue("metadata/title", self.title_edit.text())
        self.settings.setValue("metadata/description", self.description_edit.toPlainText())
        self.settings.setValue("metadata/upload_type", self.upload_type_combo.currentText())
        self.settings.setValue("metadata/access_right", self.access_right_combo.currentText())
        self.settings.setValue("metadata/keywords", [kw.strip() for kw in self.keywords_edit.text().split(",") if kw.strip()])
        self.settings.setValue("metadata/notes", self.notes_edit.toPlainText())
        self.settings.setValue("metadata/publication_date", self.publication_date_edit.date().toString("yyyy-MM-dd"))
        
        # Save funding data - DISABLED: Zenodo API has issues with funding
        # TODO: Users need to add funding information manually on Zenodo
        # funding_data = []
        # for widget in self.funding_list:
        #     fund = {}
        #     funder_edit = widget.property('funder_edit')
        #     award_number_edit = widget.property('award_number_edit') 
        #     award_title_edit = widget.property('award_title_edit')
        #     url_edit = widget.property('url_edit')
        #     
        #     # Check if all edit widgets exist
        #     if not all([funder_edit, award_number_edit, award_title_edit, url_edit]):
        #         continue
        #         
        #     funder = funder_edit.text().strip()
        #     award_number = award_number_edit.text().strip()
        #     award_title = award_title_edit.text().strip()
        #     url = url_edit.text().strip()
        #     
        #     if funder and award_number:
        #         fund["funder"] = funder
        #         fund["award_number"] = award_number
        #         if award_title:
        #             fund["award_title"] = award_title
        #         if url:
        #             fund["url"] = url
        #         funding_data.append(fund)
        #         
        # self.settings.setValue("funding", funding_data)
    
    def on_token_changed(self):
        """Handle access token change"""
        # Skip during metadata loading to avoid blocking API calls
        if getattr(self, '_loading_metadata', False):
            return
            
        token = self.token_edit.text().strip()
        sandbox = self.sandbox_checkbox.isChecked()
        self.service_factory.update_api_config(token, sandbox)
        
        # Reset connection status when token changes
        self.upload_button.setEnabled(False)
        if hasattr(self, 'connection_status_label'):
            if token:
                self.update_connection_status(False, "Token changed - test connection")
            else:
                self.update_connection_status(False, "No API token entered")
        
        if token:
            self.load_licenses()
    
    def on_sandbox_changed(self):
        """Handle sandbox checkbox change"""
        # Skip during metadata loading
        if getattr(self, '_loading_metadata', False):
            return
            
        token = self.token_edit.text().strip()
        sandbox = self.sandbox_checkbox.isChecked()
        self.service_factory.update_api_config(token, sandbox)
        
        # Reset connection status when sandbox mode changes
        self.upload_button.setEnabled(False)
        if hasattr(self, 'connection_status_label'):
            mode = "sandbox" if sandbox else "production"
            self.update_connection_status(False, f"Switched to {mode} - test connection")
    
    def on_publish_safety_changed(self):
        """Handle publish safety checkbox change"""
        safety_checked = self.publish_safety_checkbox.isChecked()
        self.publish_checkbox.setEnabled(safety_checked)
        
        # If safety checkbox is unchecked, also uncheck the publish checkbox
        if not safety_checked:
            self.publish_checkbox.setChecked(False)
    
    def test_connection(self):
        """Test the Zenodo API connection"""
        api = self.service_factory.get_repository_api()
        if not api:
            QMessageBox.warning(self, "Warning", "Please enter an access token first.")
            self.update_connection_status(False, "No API token")
            return
        
        try:
            # Test connection by trying to list depositions
            depositions = api.list_depositions()
            QMessageBox.information(self, "Success", "Connection to Zenodo API successful!")
            self.upload_button.setEnabled(True)
            self.update_connection_status(True, "Connected")
            
        except Exception as e:
            QMessageBox.critical(self, "Connection Failed", f"Failed to connect to Zenodo API:\n{str(e)}")
            self.upload_button.setEnabled(False)
            self.update_connection_status(False, f"Connection failed: {str(e)[:30]}...")
    
    def update_connection_status(self, connected: bool, message: str = ""):
        """Update the connection status indicator"""
        mode = "Sandbox" if self.sandbox_checkbox.isChecked() else "Production"
        
        if connected:
            # Upload tab indicator
            self.connection_status_label.setText("✅ Connected")
            self.connection_status_label.setStyleSheet("color: green; font-weight: bold; margin-left: 5px;")
            self.connection_status_label.setToolTip("API connection successful. Upload is available.")
            
            # Configuration tab indicator  
            if hasattr(self, 'config_connection_status_label'):
                self.config_connection_status_label.setText(f"✅ Connected to Zenodo {mode}")
                self.config_connection_status_label.setStyleSheet("color: green; font-weight: bold; padding: 5px;")
                self.config_connection_status_label.setToolTip(f"Successfully connected to Zenodo {mode} API")
        else:
            # Upload tab indicator
            self.connection_status_label.setText("❌ Not Connected")
            self.connection_status_label.setStyleSheet("color: red; font-weight: bold; margin-left: 5px;")
            tooltip = "API connection not established. Test connection in Configuration tab to enable upload."
            if message:
                tooltip += f"\nReason: {message}"
            self.connection_status_label.setToolTip(tooltip)
            
            # Configuration tab indicator
            if hasattr(self, 'config_connection_status_label'):
                self.config_connection_status_label.setText(f"❌ Not Connected ({mode})")
                self.config_connection_status_label.setStyleSheet("color: red; font-weight: bold; padding: 5px;")
                config_tooltip = f"Not connected to Zenodo {mode} API."
                if message:
                    config_tooltip += f" Reason: {message}"
                self.config_connection_status_label.setToolTip(config_tooltip)
    
    def load_licenses(self):
        """Load available licenses from Zenodo"""
        api = self.service_factory.get_repository_api()
        if not api:
            return
        
        try:
            licenses = api.get_licenses()
            if not isinstance(licenses, list):
                raise ValueError("Invalid response from Zenodo API")
                
            self.license_combo.clear()
            
            # Add common licenses first
            common_licenses = ["cc-by-4.0", "cc-by-sa-4.0", "cc0-1.0", "mit", "apache-2.0"]
            added_licenses = set()
            
            for license_id in common_licenses:
                for license_data in licenses:
                    if isinstance(license_data, dict) and license_data.get("id") == license_id:
                        title = license_data.get("title", license_id)
                        self.license_combo.addItem(f"{title} ({license_id})", license_id)
                        added_licenses.add(license_id)
                        break
            
            # Add separator
            self.license_combo.insertSeparator(len(common_licenses))
            
            # Add all other licenses
            for license_data in licenses:
                license_id = license_data.get("metadata", {}).get("id", "")
                if license_id and license_id not in added_licenses:
                    title = license_data.get("metadata", {}).get("title", license_id)
                    self.license_combo.addItem(f"{title} ({license_id})", license_id)
            
            # Set default to CC-BY-4.0
            index = self.license_combo.findData("cc-by-4.0")
            if index >= 0:
                self.license_combo.setCurrentIndex(index)
            
        except Exception as e:
            print(f"Failed to load licenses: {e}")
            # Add fallback licenses
            self.license_combo.clear()
            self.license_combo.addItem("CC BY 4.0", "cc-by-4.0")
            self.license_combo.addItem("CC BY-SA 4.0", "cc-by-sa-4.0")
            self.license_combo.addItem("CC0 1.0", "cc0-1.0")
    
    def search_communities(self, text: str):
        """Search for communities and update the combo box"""
        # Skip search during metadata loading to avoid blocking
        if getattr(self, '_loading_metadata', False):
            return
            
        api = self.service_factory.get_repository_api()
        if not api:
            return
            
        self.community_combo.clear()
        if not text:
            return
            
        try:
            communities = api.search_communities(query=text)
            for comm in communities:
                identifier = comm['metadata'].get('id', '')
                title = comm['metadata'].get('title', 'Unknown Community')
                self.community_combo.addItem(f"{title} ({identifier})", identifier)
        except Exception as e:
            print(f"Failed to search communities: {e}")
    
    def add_selected_community(self):
        """Add the currently selected community from the combo box"""
        current_data = self.community_combo.currentData()
        if current_data:
            self.add_community(current_data)
    
    def add_community(self, default_id=None, lookup: bool = True):
        """Add a new community input widget

        default_id: optional community identifier string
        lookup: whether to query the API for the community title/tooltip
        """
        # Don't add if already exists
        for i in range(len(self.communities_list)):
            if self.communities_list[i].text() == default_id:
                return
                
        container = QWidget()
        container_layout = QHBoxLayout()
        
        community_name = QLineEdit()
        community_name.setPlaceholderText("Community identifier")
        community_name.setReadOnly(True)  # Make it read-only
        if default_id:
            community_name.setText(default_id)
            # Optionally lookup the community title from the API. During bulk
            # metadata loads this should be skipped to avoid blocking network
            # I/O on the GUI thread which appears as a freeze.
            if lookup and not getattr(self, '_loading_metadata', False):
                api = self.service_factory.get_repository_api()
                if api:
                    try:
                        communities = api.search_communities(query=default_id)
                        for comm in communities:
                            if comm['metadata'].get('id') == default_id:
                                title = comm['metadata'].get('title', 'Unknown Community')
                                community_name.setToolTip(title)
                                break
                    except Exception:
                        pass
        
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self.remove_community(container, community_name))
        
        container_layout.addWidget(community_name)
        container_layout.addWidget(remove_btn)
        container.setLayout(container_layout)
        
        self.communities_layout.addWidget(container)
        self.communities_list.append(community_name)
        
        # Hide remove button if only one community
        if len(self.communities_list) == 1:
            remove_btn.hide()
        else:
            # Show all remove buttons
            for i in range(self.communities_layout.count()):
                item = self.communities_layout.itemAt(i)
                if not item:
                    continue
                    
                widget = item.widget()
                if not widget:
                    continue
                
                layout = widget.layout()
                if not layout:
                    continue
                
                if layout.count() <= 1:
                    continue
                    
                item = layout.itemAt(1)
                if not item:
                    continue
                    
                btn = item.widget()
                if isinstance(btn, QPushButton):
                    btn.show()
    
    def remove_community(self, container, community_edit):
        """Remove a community widget"""
        if len(self.communities_list) <= 1:
            return
            
        try:
            self.communities_list.remove(community_edit)
            container.setParent(None)
            container.deleteLater()
            
            # Hide remove button if only one community left
            if len(self.communities_list) == 1:
                for i in range(self.communities_layout.count()):
                    item = self.communities_layout.itemAt(i)
                    if not item:
                        continue
                        
                    widget = item.widget()
                    if not widget:
                        continue
                    
                    layout = widget.layout()
                    if not layout:
                        continue
                    
                    if layout.count() <= 1:
                        continue
                        
                    item = layout.itemAt(1)
                    if not item:
                        continue
                        
                    btn = item.widget()
                    if isinstance(btn, QPushButton):
                        btn.hide()
                                
        except (ValueError, RuntimeError):
            # In case widget is already removed or deleted
            pass
    
    def add_creator(self):
        """Add a new creator input widget"""
        creator_widget = CreatorWidget()
        
        # Add remove button
        remove_layout = QHBoxLayout()
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self.remove_creator(creator_widget, remove_layout))
        
        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.addWidget(creator_widget)
        container_layout.addLayout(remove_layout)
        container.setLayout(container_layout)
        
        remove_layout.addStretch()
        remove_layout.addWidget(remove_btn)
        
        self.creators_list.append(creator_widget)
        self.creators_widget_layout.addWidget(container)
        
        # Hide remove button if only one creator
        if len(self.creators_list) == 1:
            remove_btn.hide()
        else:
            # Show all remove buttons
            for i, widget in enumerate(self.creators_list):
                parent = widget.parent()
                if parent:
                    layout = parent.layout()
                    if layout and layout.count() > 1:
                        remove_layout = layout.itemAt(1).layout()
                        if remove_layout and remove_layout.count() > 1:
                            remove_btn = remove_layout.itemAt(1).widget()
                            if remove_btn:
                                remove_btn.show()
    
    def add_funding(self):
        """Add a new funding entry"""
        container = QWidget()
        container_layout = QFormLayout()
        
        funder_edit = QLineEdit()
        funder_edit.setPlaceholderText("e.g., Engineering and Physical Sciences Research Council")
        
        # Add autocomplete for common funders
        common_funders = Funding.get_common_funders()
        completer = QCompleter(common_funders, funder_edit)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        funder_edit.setCompleter(completer)
        
        award_number_edit = QLineEdit()
        award_number_edit.setPlaceholderText("e.g., EP/X014444/1")
        
        award_title_edit = QLineEdit()
        award_title_edit.setPlaceholderText("Full name of the award (optional)")
        
        url_edit = QLineEdit()
        url_edit.setPlaceholderText("URL to grant information (optional)")
        
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self.remove_funding(container))
        
        container_layout.addRow("Funder:", funder_edit)
        container_layout.addRow("Award Number:", award_number_edit)
        container_layout.addRow("Award Title:", award_title_edit)
        container_layout.addRow("URL:", url_edit)
        container_layout.addRow("", remove_btn)
        
        container.setLayout(container_layout)
        container.setProperty('funder_edit', funder_edit)
        container.setProperty('award_number_edit', award_number_edit)
        container.setProperty('award_title_edit', award_title_edit)
        container.setProperty('url_edit', url_edit)
        
        self.funding_layout.addWidget(container)
        self.funding_list.append(container)
        
        # Hide remove button if only one funding entry
        if len(self.funding_list) == 1:
            remove_btn.hide()
        else:
            # Show all remove buttons
            for i in range(self.funding_layout.count()):
                item = self.funding_layout.itemAt(i)
                if not item:
                    continue
                    
                widget = item.widget()
                if not widget:
                    continue
                
                layout = widget.layout()
                if not layout:
                    continue
                
                for j in range(layout.count()):
                    item = layout.itemAt(j)
                    if not item:
                        continue
                    
                    btn = item.widget()
                    if isinstance(btn, QPushButton):
                        btn.show()
    
    def remove_funding(self, container):
        """Remove a funding entry"""
        if len(self.funding_list) <= 1:
            return
        
        try:
            self.funding_list.remove(container)
            container.setParent(None)
            container.deleteLater()
            
            # Hide remove button if only one funding left
            if len(self.funding_list) == 1:
                for j in range(self.funding_list[0].layout().count()):
                    if isinstance(self.funding_list[0].layout().itemAt(j).widget(), QPushButton):
                        self.funding_list[0].layout().itemAt(j).widget().hide()
                        break
        except (ValueError, RuntimeError):
            pass
    
    def remove_creator(self, creator_widget, remove_layout, force=False):
        """Remove a creator widget"""
        if len(self.creators_list) <= 1 and not force:
            return
        
        try:
            self.creators_list.remove(creator_widget)
            container = creator_widget.parent()
            if container:
                container.setParent(None)
                container.deleteLater()
        except (ValueError, RuntimeError):
            # In case widget is already removed or deleted
            pass
        
        # Hide remove button if only one creator left
        if len(self.creators_list) == 1:
            widget = self.creators_list[0]
            parent = widget.parent()
            if parent:
                layout = parent.layout()
                if layout and layout.count() > 1:
                    remove_layout = layout.itemAt(1).layout()
                    if remove_layout and remove_layout.count() > 1:
                        remove_btn = remove_layout.itemAt(1).widget()
                        if remove_btn:
                            remove_btn.hide()
    
    def add_contributor(self):
        """Add a new contributor input widget"""
        contributor_widget = ContributorWidget()
        
        # Add remove button
        remove_layout = QHBoxLayout()
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self.remove_contributor(contributor_widget, remove_layout))
        
        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.addWidget(contributor_widget)
        container_layout.addLayout(remove_layout)
        container.setLayout(container_layout)
        
        remove_layout.addStretch()
        remove_layout.addWidget(remove_btn)
        
        self.contributors_list.append(contributor_widget)
        self.contributors_widget_layout.addWidget(container)
    
    def remove_contributor(self, contributor_widget, remove_layout):
        """Remove a contributor widget"""
        try:
            self.contributors_list.remove(contributor_widget)
            container = contributor_widget.parent()
            if container:
                container.setParent(None)
                container.deleteLater()
        except (ValueError, RuntimeError):
            # In case widget is already removed or deleted
            pass
    
    def browse_file(self):
        """Browse for a file to upload"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Data File", "", 
            "ZIP files (*.zip);;All files (*.*)"
        )
        if file_path:
            self.file_path_edit.setText(file_path)
    
    def create_zip_from_folder(self):
        """Create a ZIP file from a selected folder"""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder to ZIP")
        if not folder_path:
            return
        
        # Ask where to save the ZIP file
        zip_path, _ = QFileDialog.getSaveFileName(
            self, "Save ZIP file as", 
            os.path.join(os.path.dirname(folder_path), os.path.basename(folder_path) + ".zip"),
            "ZIP files (*.zip)"
        )
        
        if not zip_path:
            return
        
        try:
            zip_path = create_zip_from_folder(folder_path, zip_path)
            self.file_path_edit.setText(zip_path)
            QMessageBox.information(self, "Success", f"ZIP file created successfully:\n{zip_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create ZIP file:\n{str(e)}")
    
    def get_metadata(self) -> Dict[str, Any]:
        """Extract metadata from the form"""
        # Get measurement parameters from the dynamic widget
        measurement_params = self.measurement_params_widget.get_parameters()
        
        # Create ED parameters using the dynamic parameters
        ed_params = EDParameters(parameters=measurement_params)
        
        # Create creators list
        creators = []
        for creator_widget in self.creators_list:
            creator_data = creator_widget.get_data()
            if creator_data.get("name"):
                creators.append(Creator(
                    name=creator_data["name"],
                    affiliation=creator_data.get("affiliation"),
                    orcid=creator_data.get("orcid")
                    # Note: type field removed - only for Contributors, not Creators
                ))
        
        # Create contributors list
        contributors = []
        for contributor_widget in self.contributors_list:
            contributor_data = contributor_widget.get_data()
            if contributor_data.get("name"):
                contributors.append(Contributor(
                    name=contributor_data["name"],
                    affiliation=contributor_data.get("affiliation"),
                    orcid=contributor_data.get("orcid"),
                    type=contributor_data.get("type")
                ))
        
        # Create metadata object
        metadata = ZenodoMetadata(
            title=self.title_edit.text().strip(),
            description=self.description_edit.toPlainText().strip(),
            creators=creators,
            contributors=contributors,
            upload_type=self.upload_type_combo.currentText(),
            access_right=self.access_right_combo.currentText(),
            license=self.license_combo.currentData(),
            keywords=[kw.strip() for kw in self.keywords_edit.text().split(",") if kw.strip()],
            publication_date=self.publication_date_edit.date().toString("yyyy-MM-dd"),
            notes=self.notes_edit.toPlainText().strip() if self.notes_edit.toPlainText().strip() else None,
            ed_parameters=ed_params
        )
        
        # Add funding if available
        funding = []
        for i in range(len(self.funding_list)):
            widget = self.funding_list[i]
            funder_edit = widget.property('funder_edit')
            award_number_edit = widget.property('award_number_edit')
            award_title_edit = widget.property('award_title_edit')
            url_edit = widget.property('url_edit')
            
            # Check if all edit widgets exist
            if not all([funder_edit, award_number_edit, award_title_edit, url_edit]):
                continue
                
            funder = funder_edit.text().strip()
            award_number = award_number_edit.text().strip()
            award_title = award_title_edit.text().strip()
            url = url_edit.text().strip()
            
            if funder and award_number:
                fund = Funding(
                    funder=funder,
                    award_number=award_number,
                    award_title=award_title if award_title else None,
                    url=url if url else None
                )
                funding.append(fund)
        
        if funding:
            funding_data = funding
            metadata.funding = funding_data
        
        return metadata.to_dict()
    
    def validate_metadata(self):
        """Validate the entered metadata"""
        try:
            metadata = self.get_metadata()
            validator = self.service_factory.get_metadata_validator()
            
            if not validator.validate(metadata):
                errors = validator.get_errors()
                error_msg = "\n".join([f"• {error}" for error in errors])
                QMessageBox.warning(self, "Validation Error", f"Validation failed:\n\n{error_msg}")
                return False
            
            QMessageBox.information(self, "Validation Success", "Metadata validation passed!")
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "Validation Error", f"Error validating metadata:\n{str(e)}")
            return False
    
    def handle_upload_button_click(self):
        """Handle upload button click - either start upload or cancel"""
        if hasattr(self, 'upload_worker') and self.upload_worker and self.upload_worker.isRunning():
            # Upload is running, so cancel it
            self.cancel_upload()
        else:
            # No upload running, so start one
            self.start_upload()
    
    def start_upload(self):
        """Start the upload process"""
        if not self.service_factory.has_api_services():
            QMessageBox.warning(self, "Error", "Please configure and test the API connection first.")
            return
        
        if not self.file_path_edit.text():
            QMessageBox.warning(self, "Error", "Please select a file to upload.")
            return
        
        if self.validate_checkbox.isChecked() and not self.validate_metadata():
            return
        
        # Cancel any existing upload
        if hasattr(self, 'upload_worker') and self.upload_worker and self.upload_worker.isRunning():
            self.cancel_upload()
            return
        
        # Initialize upload worker with services
        metadata = self.get_metadata()
        upload_service = self.service_factory.get_upload_service()
        
        self.upload_worker = ModularUploadWorker(
            upload_service,
            metadata,
            self.file_path_edit.text(),
            self.publish_checkbox.isChecked()
        )
        
        # Connect signals
        self.upload_worker.progress_updated.connect(self.progress_bar.setValue)
        self.upload_worker.status_updated.connect(self.status_label.setText)
        self.upload_worker.upload_completed.connect(self.on_upload_completed)
        self.upload_worker.upload_failed.connect(self.on_upload_failed)
        self.upload_worker.finished.connect(self.on_upload_finished)
        
        # Update UI for upload state
        self.upload_button.setText("Cancel Upload")
        self.upload_button.setEnabled(True)  # Keep enabled for cancelling
        self.validate_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.results_text.clear()
        
        # Start worker
        self.upload_worker.start()
        
    def cancel_upload(self):
        """Cancel the current upload"""
        if hasattr(self, 'upload_worker') and self.upload_worker and self.upload_worker.isRunning():
            self.status_label.setText("Cancelling upload...")
            self.upload_worker.cancel()
            # Wait up to 5 seconds for worker to finish
            if not self.upload_worker.wait(5000):
                self.upload_worker.terminate()
                self.upload_worker.wait()
            self.on_upload_finished()
    
    def on_upload_finished(self):
        """Clean up after upload completion or cancellation"""
        # Reset UI state
        self.upload_button.setText("Start Upload")
        self.upload_button.setEnabled(True)
        self.validate_button.setEnabled(True)
        
        # Clean up worker reference
        if hasattr(self, 'upload_worker'):
            if self.upload_worker:
                self.upload_worker.deleteLater()
            self.upload_worker = None
    
    def on_upload_completed(self, result: Dict[str, Any]):
        """Handle successful upload"""
        # Format result summary
        record_url = result.get("links", {}).get("record", "")
        if not record_url:
            # Try alternative URL paths
            record_url = result.get("links", {}).get("html", "")
        
        doi = result.get("metadata", {}).get("doi", "")
        if not doi:
            # Try prereserved DOI
            prereserve = result.get("metadata", {}).get("prereserve_doi", {})
            if prereserve:
                doi = prereserve.get("doi", "")
        
        summary = "<p>✅ <b>Upload completed successfully!</b></p>"
        if record_url:
            summary += f"<p>📄 <b>Record URL:</b> <a href='{record_url}'>{record_url}</a></p>"
        if doi:
            summary += f"<p>🏷️ <b>DOI:</b> {doi}</p>"
            
        # Add some helpful information
        if result.get("submitted", False):
            summary += "<p>📢 Your record has been published and is now live!</p>"
        else:
            summary += "<p>📝 Your record has been saved as a draft. You can publish it later from the Zenodo website.</p>"
            
        # Add manual steps reminder
        summary += "<br><p><b>⚠️ Manual Steps Required:</b></p>"
        summary += "<p>Please visit your record on Zenodo to manually add:</p>"
        summary += "<ul><li>Funding information (grants)</li>"
        summary += "<li>Creator roles/types for each author</li></ul>"
        summary += "<p><i>These features are not fully supported via the API yet.</i></p>"
        
        self.results_text.setHtml(summary)
        
        # Save settings after successful upload
        self.save_settings()
        
        # Show success message with manual steps reminder
        success_msg = "Upload completed successfully!\n\n"
        success_msg += "⚠️ Don't forget to manually add on Zenodo:\n"
        success_msg += "• Funding information (grants)\n"
        success_msg += "• Creator roles/types for each author"
        QMessageBox.information(self, "Success", success_msg)
    
    def on_upload_failed(self, error_message: str):
        """Handle upload failure"""        
        # Display detailed error message
        error_text = f"❌ Upload failed:\n\n{error_message}"
        
        # Add troubleshooting tips
        error_text += "\n\n🔧 Troubleshooting tips:"
        error_text += "\n• Check your internet connection"
        error_text += "\n• Verify your API token has the correct permissions (deposit:write, deposit:actions)"
        error_text += "\n• Try again with a smaller file if the upload timed out"
        error_text += "\n• Check if you're using sandbox mode for testing"
        
        self.results_text.setText(error_text)
        
        # Show error dialog with option to copy error details
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Upload Failed")
        msg_box.setText("The upload failed. See details below.")
        msg_box.setDetailedText(error_message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
        QMessageBox.critical(self, "Upload Failed", f"Failed to upload:\n{error_message}")
    
    def closeEvent(self, a0):
        """Handle application close"""
        self.save_settings()
        super().closeEvent(a0)
    
    def reset_metadata(self):
        """Reset all metadata fields to their default values using the clean template system"""
        # Ask for confirmation
        reply = QMessageBox.question(
            self, "Confirm Reset",
            "Are you sure you want to reset all metadata fields?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Get default template and populate GUI
                template_service = self.service_factory.get_template_service()
                default_template = template_service.get_default_template()
                
                # Use the same clean loading mechanism as JSON loading
                populate_gui_from_template(self, default_template)
                
                QMessageBox.information(self, "Reset Complete", "All fields have been reset to default values.")
            except Exception as e:
                QMessageBox.critical(self, "Reset Failed", f"Failed to reset fields:\n{str(e)}")
    
    def load_metadata_from_json(self):
        """Load metadata from a JSON file using the new template system"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Metadata JSON File", "", 
            "JSON files (*.json);;All files (*.*)"
        )
        
        if not file_path:
            return
            
        try:
            # Use template service to load the data
            template_service = self.service_factory.get_template_service()
            template = template_service.load_user_template(file_path)
            
            # Populate GUI from template (this handles signal blocking internally)
            populate_gui_from_template(self, template)
            
            QMessageBox.information(self, "Success", "Metadata loaded successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load metadata:\n{str(e)}")
    
    def save_metadata_to_json(self):
        """Save current metadata to a JSON file using the template system"""
        try:
            # Create template from current GUI state
            template = self._gui_to_template()
            
            # Ask where to save
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Metadata As", "", 
                "JSON files (*.json);;All files (*.*)"
            )
            
            if not file_path:
                return
                
            # Add .json extension if not present
            if not file_path.lower().endswith('.json'):
                file_path += '.json'
                
            # Use template service to save
            template_service = self.service_factory.get_template_service()
            success = template_service.save_template(template, file_path)
            
            if success:
                QMessageBox.information(self, "Success", "Metadata saved successfully!")
            else:
                QMessageBox.critical(self, "Error", "Failed to save metadata file")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save metadata:\n{str(e)}")
    
    def _gui_to_template(self):
        """Extract current GUI state into a MetadataTemplate"""
        from ..services.templates import MetadataTemplate, TemplateCreator, TemplateFunding, TemplateCommunity, TemplateEDParameters
        
        # Basic fields
        template = MetadataTemplate(
            title=self.title_edit.text(),
            description=self.description_edit.toPlainText(),
            upload_type=self.upload_type_combo.currentText(),
            access_right=self.access_right_combo.currentText(),
            license=self.license_combo.currentData() or "cc-by-4.0",
            keywords=[k.strip() for k in self.keywords_edit.text().split(',') if k.strip()],
            notes=self.notes_edit.toPlainText(),
            publication_date=self.publication_date_edit.date().toString("yyyy-MM-dd")
        )
        
        # Authors
        template.creators = []
        for creator_widget in self.creators_list:
            creator_data = creator_widget.get_data()
            if creator_data.get("name"):  # Only add creators with names
                template.creators.append(TemplateCreator(
                    name=creator_data.get("name", ""),
                    affiliation=creator_data.get("affiliation", ""),
                    orcid=creator_data.get("orcid", "")
                    # Note: type field removed - TemplateCreator is for creators only
                ))
        
        # Funding
        template.grants = []
        for container in self.funding_list:
            funder_edit = container.property('funder_edit')
            award_number_edit = container.property('award_number_edit')
            award_title_edit = container.property('award_title_edit')
            url_edit = container.property('url_edit')
            
            # Check if all edit widgets exist
            if not all([funder_edit, award_number_edit, award_title_edit, url_edit]):
                continue
            
            funder = funder_edit.text().strip()
            award_number = award_number_edit.text().strip()
            award_title = award_title_edit.text().strip()
            url = url_edit.text().strip()
            
            if funder and award_number:
                template.grants.append(TemplateFunding(
                    funder=funder,
                    award_number=award_number,
                    award_title=award_title,
                    url=url if url else None
                ))
        
        # Communities
        template.communities = []
        for community_edit in self.communities_list:
            identifier = community_edit.text().strip()
            if identifier:
                template.communities.append(TemplateCommunity(identifier=identifier))
        
        # Measurement Parameters (dynamic)
        template.ed_parameters = TemplateEDParameters(
            parameters=self.measurement_params_widget.get_parameters()
        )
        
        return template
    
    def create_config_tab(self) -> QWidget:
        """Create the configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # API Configuration
        api_group = QGroupBox("Zenodo API Configuration")
        api_layout = QFormLayout()
        
        self.token_edit = QLineEdit()
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.textChanged.connect(self.on_token_changed)
        
        self.sandbox_checkbox = QCheckBox("Use Sandbox (for testing)")
        self.sandbox_checkbox.setChecked(True)
        self.sandbox_checkbox.stateChanged.connect(self.on_sandbox_changed)
        
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        
        # Connection status indicator for Configuration tab
        self.config_connection_status_label = QLabel("❌ Not Connected")
        self.config_connection_status_label.setStyleSheet("color: red; font-weight: bold; padding: 5px;")
        self.config_connection_status_label.setToolTip("API connection status")
        
        api_layout.addRow("Access Token:", self.token_edit)
        api_layout.addRow("", self.sandbox_checkbox)
        api_layout.addRow("", self.test_button)
        api_layout.addRow("Connection Status:", self.config_connection_status_label)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # Add notice for portable version
        if is_frozen_executable():
            portable_notice = QLabel("""
            <p><b>ℹ️ Portable Version Notice:</b><br>
            This is the portable executable version. Settings are not saved between sessions for privacy and security. 
            You'll need to enter your access token each time you start the application.</p>
            """)
            portable_notice.setWordWrap(True)
            portable_notice.setStyleSheet("QLabel { background-color: #e8f4fd; padding: 10px; border: 1px solid #b3d9f2; border-radius: 5px; }")
            layout.addWidget(portable_notice)
        
        # Instructions
        instructions = QLabel("""
        <h3>Getting Started:</h3>
        <ol>
        <li>Create a Zenodo account at <a href="https://zenodo.org">zenodo.org</a> (or <a href="https://sandbox.zenodo.org">sandbox.zenodo.org</a> for testing)</li>
        <li>Go to Applications → Personal access tokens</li>
        <li>Create a new token with 'deposit:write' and 'deposit:actions' scopes</li>
        <li>Enter the token above and test the connection</li>
        <li>Fill in your metadata and upload your data</li>
        </ol>
        """)
        instructions.setWordWrap(True)
        instructions.setOpenExternalLinks(True)
        layout.addWidget(instructions)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def create_metadata_tab(self) -> QWidget:
        """Create the metadata input tab"""
        tab = QWidget()
        
        # Create main tab layout
        tab_layout = QVBoxLayout()
        
        # Add template control buttons at the top
        top_button_layout = QHBoxLayout()
        
        load_json_btn = QPushButton("📥 Load from JSON...")
        load_json_btn.clicked.connect(self.load_metadata_from_json)
        load_json_btn.setToolTip("Load metadata template from JSON file")
        
        save_json_btn = QPushButton("💾 Save to JSON...")
        save_json_btn.clicked.connect(self.save_metadata_to_json)
        save_json_btn.setToolTip("Save current metadata as JSON template")
        
        reset_btn = QPushButton("🔄 Reset All Fields")
        reset_btn.clicked.connect(self.reset_metadata)
        reset_btn.setToolTip("Clear all fields and reset to defaults")
        
        top_button_layout.addWidget(load_json_btn)
        top_button_layout.addWidget(save_json_btn)
        top_button_layout.addWidget(reset_btn)
        top_button_layout.addStretch()  # Push buttons to the left
        
        tab_layout.addLayout(top_button_layout)
        
        # Create a scrollable container for the form content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Create the container widget
        container = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)  # Normal spacing between sections
        layout.setContentsMargins(10, 10, 10, 10)  # Normal margins around form
        container.setLayout(layout)
        
        # Basic Information
        basic_box = QCollapsibleBox("Basic Information")
        basic_layout = QFormLayout()
        
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Title of your dataset")
        
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Detailed description...")
        self.description_edit.setMaximumHeight(100)
        
        self.upload_type_combo = QComboBox()
        self.upload_type_combo.addItems([
            "dataset", "publication", "poster", "presentation", 
            "image", "video", "software", "lesson", "physicalobject", "other"
        ])
        self.upload_type_combo.setCurrentText("dataset")
        
        self.access_right_combo = QComboBox()
        self.access_right_combo.addItems(["open", "embargoed", "restricted", "closed"])
        
        self.license_combo = QComboBox()
        self.license_combo.addItem("Loading licenses...", "")
        
        basic_layout.addRow("Title*:", self.title_edit)
        basic_layout.addRow("Description*:", self.description_edit)
        basic_layout.addRow("Upload Type*:", self.upload_type_combo)
        basic_layout.addRow("Access Rights*:", self.access_right_combo)
        basic_layout.addRow("License*:", self.license_combo)
        
        basic_box.setContentLayout(basic_layout)
        layout.addWidget(basic_box)
        
        # Authors
        creators_box = QCollapsibleBox("Creators", collapsed=True)
        creators_layout = QVBoxLayout()
        
        self.creators_widget = QWidget()
        self.creators_widget_layout = QVBoxLayout()
        self.creators_widget.setLayout(self.creators_widget_layout)
        
        add_creator_btn = QPushButton("Add Creator")
        add_creator_btn.clicked.connect(self.add_creator)
        
        creators_layout.addWidget(self.creators_widget)
        creators_layout.addWidget(add_creator_btn)
        creators_box.setContentLayout(creators_layout)
        layout.addWidget(creators_box)
        
        # Add first creator by default
        self.add_creator()
        
        # Contributors section
        contributors_box = QCollapsibleBox("Contributors (Optional)", collapsed=True)
        contributors_layout = QVBoxLayout()
        
        self.contributors_widget = QWidget()
        self.contributors_widget_layout = QVBoxLayout()
        self.contributors_widget.setLayout(self.contributors_widget_layout)
        
        add_contributor_btn = QPushButton("Add Contributor")
        add_contributor_btn.clicked.connect(self.add_contributor)
        
        contributors_layout.addWidget(self.contributors_widget)
        contributors_layout.addWidget(add_contributor_btn)
        contributors_box.setContentLayout(contributors_layout)
        layout.addWidget(contributors_box)
        
        # Additional metadata
        additional_box = QCollapsibleBox("Additional Information", collapsed=True)
        additional_layout = QFormLayout()
        
        self.keywords_edit = QLineEdit()
        self.keywords_edit.setPlaceholderText("keyword1, keyword2, keyword3")
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setPlaceholderText("Additional notes...")
        
        self.publication_date_edit = QDateEdit()
        self.publication_date_edit.setDate(QDate.currentDate())
        self.publication_date_edit.setCalendarPopup(True)
        
        additional_layout.addRow("Keywords:", self.keywords_edit)
        additional_layout.addRow("Publication Date:", self.publication_date_edit)
        additional_layout.addRow("Notes:", self.notes_edit)
        
        additional_box.setContentLayout(additional_layout)
        layout.addWidget(additional_box)
        
        # Funding - DISABLED: Zenodo API has issues with funding
        # TODO: Users need to add funding information manually on Zenodo
        # funding_box = QCollapsibleBox("Funding", collapsed=True)
        # funding_layout = QVBoxLayout()
        # 
        # # Widget to hold the list of funding entries
        # self.funding_widget = QWidget()
        # self.funding_layout = QVBoxLayout()
        # self.funding_widget.setLayout(self.funding_layout)
        # self.funding_list = []
        # 
        # # Add funding button
        # add_funding_btn = QPushButton("Add Funding")
        # add_funding_btn.clicked.connect(self.add_funding)
        # 
        # funding_layout.addWidget(self.funding_widget)
        # funding_layout.addWidget(add_funding_btn)
        # funding_box.setContentLayout(funding_layout)
        # layout.addWidget(funding_box)
        
        # Initialize funding list as empty (to avoid errors)
        self.funding_list = []
        
        # Communities
        communities_box = QCollapsibleBox("Communities", collapsed=True)
        communities_layout = QVBoxLayout()
        
        # Create search layout
        search_layout = QHBoxLayout()
        self.community_search = QLineEdit()
        self.community_search.setPlaceholderText("Search for communities...")
        self.community_search.textChanged.connect(self.search_communities)
        
        self.community_combo = QComboBox()
        self.community_combo.setMinimumWidth(300)
        self.community_combo.setEditable(False)
        
        add_community_btn = QPushButton("Add")
        add_community_btn.clicked.connect(self.add_selected_community)
        
        search_layout.addWidget(self.community_search)
        search_layout.addWidget(self.community_combo)
        search_layout.addWidget(add_community_btn)
        communities_layout.addLayout(search_layout)
        
        # Added communities list
        self.communities_widget = QWidget()
        self.communities_layout = QVBoxLayout()
        self.communities_widget.setLayout(self.communities_layout)
        self.communities_list = []
        
        communities_layout.addWidget(self.communities_widget)
        communities_box.setContentLayout(communities_layout)
        layout.addWidget(communities_box)
        
        # Add default MicroED community (don't attempt API lookup during startup)
        self.add_community("microed", lookup=False)
        
        # Experimental Parameters (dynamic)
        experimental_params_box = QCollapsibleBox("Experimental Parameters")
        experimental_params_layout = QVBoxLayout()
        
        self.measurement_params_widget = MeasurementParametersWidget()
        experimental_params_layout.addWidget(self.measurement_params_widget)
        
        experimental_params_box.setContentLayout(experimental_params_layout)
        layout.addWidget(experimental_params_box)
        
        # Set up scrolling
        scroll_area.setWidget(container)
        
        # Add scroll area to main tab layout
        tab_layout.addWidget(scroll_area)
        tab.setLayout(tab_layout)
        
        return tab
    
    def create_upload_tab(self) -> QWidget:
        """Create the upload tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # File selection
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout()
        
        file_select_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select your .zip file containing the electron diffraction data")
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_file)
        
        file_select_layout.addWidget(self.file_path_edit)
        file_select_layout.addWidget(self.browse_button)
        
        self.create_zip_button = QPushButton("Create ZIP from Folder...")
        self.create_zip_button.clicked.connect(self.create_zip_from_folder)
        
        file_layout.addLayout(file_select_layout)
        file_layout.addWidget(self.create_zip_button)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Upload options
        options_group = QGroupBox("Upload Options")
        options_layout = QVBoxLayout()
        
        self.validate_checkbox = QCheckBox("Validate metadata before upload")
        self.validate_checkbox.setChecked(True)
        
        self.publish_safety_checkbox = QCheckBox("I understand that publishing is irreversible and confirm I want to publish")
        self.publish_safety_checkbox.stateChanged.connect(self.on_publish_safety_changed)

        self.publish_checkbox = QCheckBox("Publish immediately (cannot be undone!)")
        self.publish_checkbox.setEnabled(False)  # Disabled by default
        
        options_layout.addWidget(self.validate_checkbox)
        options_layout.addWidget(self.publish_safety_checkbox)
        options_layout.addWidget(self.publish_checkbox)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Progress and controls
        controls_layout = QHBoxLayout()
        
        self.upload_button = QPushButton("Start Upload")
        self.upload_button.clicked.connect(self.handle_upload_button_click)
        self.upload_button.setEnabled(False)
        
        # Connection status indicator
        self.connection_status_label = QLabel("❌ Not Connected")
        self.connection_status_label.setStyleSheet("color: red; font-weight: bold; margin-left: 5px;")
        self.connection_status_label.setToolTip("API connection status. Test connection in Configuration tab to enable upload.")
        
        self.validate_button = QPushButton("Validate Metadata")
        self.validate_button.clicked.connect(self.validate_metadata)
        
        controls_layout.addWidget(self.validate_button)
        controls_layout.addWidget(self.upload_button)
        controls_layout.addWidget(self.connection_status_label)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.status_label = QLabel("Ready to upload")
        
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        
        # Results
        self.results_text = QTextBrowser()
        self.results_text.setMaximumHeight(150)
        self.results_text.setPlaceholderText("Upload results will appear here...")
        # QTextBrowser natively supports clickable links
        self.results_text.setReadOnly(True)
        self.results_text.setOpenExternalLinks(True)
        
        layout.addWidget(QLabel("Results:"))
        layout.addWidget(self.results_text)
        
        # Add reminder about manual steps
        manual_steps_label = QLabel()
        manual_steps_label.setText(
            "<p><b>ℹ️ Important Reminder:</b> After uploading, please visit your record on Zenodo to manually add:</p>"
            "<ul><li><b>Funding information</b> (grants/awards)</li>"
            "<li><b>Creator roles/types</b> for each author (e.g., Conceptualization, Data curation, etc.)</li></ul>"
            "<p><i>These features are not fully supported via the API yet.</i></p>"
        )
        manual_steps_label.setWordWrap(True)
        manual_steps_label.setStyleSheet("QLabel { background-color: #f0f8ff; padding: 10px; border: 1px solid #ccc; border-radius: 5px; }")
        layout.addWidget(manual_steps_label)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
