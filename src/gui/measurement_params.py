"""
Dynamic measurement parameters widget

This widget allows users to add/remove measurement parameters dynamically
and formats them as an HTML table for Zenodo deposition.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QScrollArea, QFrame, QComboBox,
    QTextEdit, QTabWidget, QTextBrowser
)
from PyQt6.QtCore import Qt, QTimer
from typing import Dict, List
from .widgets import QCollapsibleBox


class MeasurementParameterRow(QWidget):
    """A single measurement parameter row with key, value, and section fields"""
    
    def __init__(self, key: str = "", value: str = "", section: str = "", remove_callback=None):
        super().__init__()
        self.remove_callback = remove_callback
        self.init_ui(key, value, section)
    
    def init_ui(self, key: str, value: str, section: str):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Section combo box
        self.section_combo = QComboBox()
        self.section_combo.setEditable(True)
        self.section_combo.addItems([
            "",  # Empty option
            "General",
            "Instrumental", 
            "Sample description",
            "Experimental",
            "Data collection",
            "Software & Files"
        ])
        self.section_combo.setCurrentText(section)
        self.section_combo.setToolTip("Group parameters into sections for better organization")
        
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("Parameter name (e.g., 'Instrument')")
        self.key_edit.setText(key)
        
        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("Value (e.g., 'Rigaku XtaLAB Synergy-ED')")
        self.value_edit.setText(value)
        
        self.remove_btn = QPushButton("❌")
        self.remove_btn.setMaximumWidth(30)
        self.remove_btn.setToolTip("Remove this parameter")
        self.remove_btn.clicked.connect(self.remove_self)
        
        layout.addWidget(QLabel("Section:"))
        layout.addWidget(self.section_combo, 1)
        layout.addWidget(QLabel("Parameter:"))
        layout.addWidget(self.key_edit, 2)  # Give more space to key
        layout.addWidget(QLabel("Value:"))
        layout.addWidget(self.value_edit, 3)  # Give most space to value
        layout.addWidget(self.remove_btn)
        
        self.setLayout(layout)
    
    def remove_self(self):
        """Remove this row"""
        if self.remove_callback:
            self.remove_callback(self)
    
    def get_data(self) -> tuple:
        """Get the section, key, value tuple"""
        return (self.section_combo.currentText().strip(), 
                self.key_edit.text().strip(), 
                self.value_edit.text().strip())
    
    def set_data(self, key: str, value: str, section: str = ""):
        """Set the section, key, value"""
        self.section_combo.setCurrentText(section)
        self.key_edit.setText(key)
        self.value_edit.setText(value)


class MeasurementParametersWidget(QWidget):
    """Widget for managing dynamic measurement parameters"""
    
    def __init__(self):
        super().__init__()
        self.parameter_rows = []
        self.init_ui()
        
        # Add some default parameters
        self.add_default_parameters()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header with add button
        header_layout = QHBoxLayout()
        header_label = QLabel("Measurement Parameters:")
        header_label.setStyleSheet("font-weight: bold;")
        
        self.add_btn = QPushButton("➕ Add Parameter")
        self.add_btn.clicked.connect(self.on_add_button_clicked)
        
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(self.add_btn)
        
        layout.addLayout(header_layout)
        
        # Scrollable area for parameters
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMaximumHeight(300)  # Limit height
        
        self.parameters_widget = QWidget()
        self.parameters_layout = QVBoxLayout()
        self.parameters_layout.setSpacing(5)
        self.parameters_widget.setLayout(self.parameters_layout)
        
        self.scroll_area.setWidget(self.parameters_widget)
        layout.addWidget(self.scroll_area)

        # HTML Preview in collapsible box
        preview_box = QCollapsibleBox("HTML Table Preview", collapsed=True)
        preview_content_layout = QVBoxLayout()
        
        # Preview header with refresh button
        preview_header = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setMaximumWidth(100)
        self.refresh_btn.setToolTip("Refresh the HTML preview")
        self.refresh_btn.clicked.connect(self.update_preview)
        
        self.copy_html_btn = QPushButton("📋 Copy HTML")
        self.copy_html_btn.setMaximumWidth(100)
        self.copy_html_btn.setToolTip("Copy HTML code to clipboard")
        self.copy_html_btn.clicked.connect(self.copy_html_to_clipboard)
        
        preview_header.addStretch()
        preview_header.addWidget(self.refresh_btn)
        preview_header.addWidget(self.copy_html_btn)
        
        preview_content_layout.addLayout(preview_header)        # Tabbed preview (rendered and source)
        self.preview_tabs = QTabWidget()
        
        # Rendered HTML tab
        self.rendered_view = QTextBrowser()
        self.rendered_view.setMaximumHeight(200)
        self.rendered_view.document().setDefaultStyleSheet("""
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f0f0f0; font-weight: bold; }
            .section-header { background-color: #e0e0e0; font-weight: bold; }
        """)
        self.preview_tabs.addTab(self.rendered_view, "📊 Rendered Table")
        
        # HTML source tab
        self.source_view = QTextEdit()
        self.source_view.setMaximumHeight(200)
        self.source_view.setReadOnly(True)
        self.source_view.setFont(self.source_view.font())
        font = self.source_view.font()
        font.setFamily("Consolas, Monaco, monospace")
        font.setPointSize(9)
        self.source_view.setFont(font)
        self.source_view.setStyleSheet("""
            QTextEdit {
                background-color: #f8f8f8;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        self.preview_tabs.addTab(self.source_view, "🔧 HTML Source")
        
        preview_content_layout.addWidget(self.preview_tabs)
        preview_box.setContentLayout(preview_content_layout)
        layout.addWidget(preview_box)
        
        self.setLayout(layout)
    
    def add_default_parameters(self):
        """Add common measurement parameters with suggested sections"""
        defaults = [
            ("Instrument", "", "Instrumental"),
            ("Detector", "", "Instrumental"),
            ("Accelerating Voltage", "", "Instrumental"),
            ("Wavelength", "", "Instrumental"),
            ("Collection temperature", "", "Experimental"),
            ("Sample Composition", "", "Sample description")
        ]
        
        for key, value, section in defaults:
            self.add_parameter(key, value, section)
    
    def on_add_button_clicked(self):
        """Handle add button click (wrapper to avoid PyQt6 checked parameter)"""
        self.add_parameter()
    
    def add_parameter(self, key: str = "", value: str = "", section: str = ""):
        """Add a new parameter row"""
        row = MeasurementParameterRow(key, value, section, self.remove_parameter)
        
        # Connect text changes to update preview
        row.key_edit.textChanged.connect(self.update_preview)
        row.value_edit.textChanged.connect(self.update_preview)
        row.section_combo.currentTextChanged.connect(self.update_preview)
        
        self.parameter_rows.append(row)
        self.parameters_layout.addWidget(row)
        
        self.update_remove_buttons()
        self.update_preview()
    
    def remove_parameter(self, row: MeasurementParameterRow):
        """Remove a parameter row"""
        if len(self.parameter_rows) <= 1:
            return  # Always keep at least one row
        
        if row in self.parameter_rows:
            self.parameter_rows.remove(row)
            row.setParent(None)
            row.deleteLater()
            
            self.update_remove_buttons()
            self.update_preview()
    
    def update_remove_buttons(self):
        """Show/hide remove buttons based on row count"""
        show_remove = len(self.parameter_rows) > 1
        for row in self.parameter_rows:
            row.remove_btn.setVisible(show_remove)
    
    def update_preview(self):
        """Update the HTML preview with both rendered and source views"""
        html_table = self.generate_html_table()
        
        if not html_table:
            # Show placeholder when no parameters
            self.rendered_view.setHtml("<p><em>No parameters to display. Add some parameters above to see the HTML table preview.</em></p>")
            self.source_view.setPlainText("<!-- No parameters to display -->")
            return
        
        # Update rendered view - QTextEdit can render HTML
        self.rendered_view.setHtml(html_table)
        
        # Update source view with formatted HTML
        formatted_html = self.format_html_source(html_table)
        self.source_view.setPlainText(formatted_html)
    
    def format_html_source(self, html: str) -> str:
        """Format HTML source for better readability"""
        if not html:
            return ""
        
        # Simple HTML formatting - add line breaks and indentation
        formatted = html.replace('<table', '\n<table')
        formatted = formatted.replace('<thead>', '\n  <thead>')
        formatted = formatted.replace('<tbody>', '\n  <tbody>')
        formatted = formatted.replace('<tr', '\n    <tr')
        formatted = formatted.replace('<th', '\n      <th')
        formatted = formatted.replace('<td', '\n      <td')
        formatted = formatted.replace('</thead>', '\n  </thead>')
        formatted = formatted.replace('</tbody>', '\n  </tbody>')
        formatted = formatted.replace('</tr>', '\n    </tr>')
        formatted = formatted.replace('</table>', '\n</table>')
        
        # Clean up extra whitespace
        lines = [line.strip() for line in formatted.split('\n') if line.strip()]
        return '\n'.join(lines)
    
    def copy_html_to_clipboard(self):
        """Copy HTML source to clipboard"""
        html_table = self.generate_html_table()
        if html_table:
            # Copy to clipboard
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(html_table)
            
            # Show temporary feedback
            original_text = self.copy_html_btn.text()
            self.copy_html_btn.setText("✅ Copied!")
            
            # Reset button text after 2 seconds
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2000, lambda: self.copy_html_btn.setText(original_text))
    
    def get_parameters(self) -> Dict[str, str]:
        """Get all parameters as a dictionary (for backward compatibility)"""
        params = {}
        for row in self.parameter_rows:
            section, key, value = row.get_data()
            if key and value:  # Only include non-empty pairs
                params[key] = value
        return params
    
    def get_parameters_with_sections(self) -> Dict[str, List[tuple]]:
        """Get parameters organized by sections"""
        sections = {}
        for row in self.parameter_rows:
            section, key, value = row.get_data()
            if key and value:  # Only include non-empty pairs
                section = section or "General"  # Default section
                if section not in sections:
                    sections[section] = []
                sections[section].append((key, value))
        return sections
    
    def set_parameters(self, params: Dict[str, str]):
        """Set parameters from a dictionary"""
        # Clear existing rows
        for row in self.parameter_rows[:]:
            row.setParent(None)
            row.deleteLater()
        self.parameter_rows.clear()
        
        # Add parameters from dict
        if params:
            for key, value in params.items():
                self.add_parameter(key, value)
        else:
            # Add at least one empty row if no params
            self.add_parameter()
    
    def clear_parameters(self):
        """Clear all parameters"""
        self.set_parameters({})
    
    def generate_html_table(self) -> str:
        """Generate HTML table for Zenodo with sections (no header row)"""
        sections = self.get_parameters_with_sections()
        
        if not sections:
            return ""
        
        html = "<table border='1' style='border-collapse: collapse;'>\n"
        html += "  <tbody>\n"
        
        # Sort sections so "General" comes first if it exists
        section_order = ["General"] + [s for s in sorted(sections.keys()) if s != "General"]
        
        first_section = True
        for section_name in section_order:
            if section_name not in sections:
                continue
                
            # Add empty row for spacing between sections (except before first section)
            if not first_section:
                html += "    <tr>\n"
                html += "      <td style='padding: 8px; border: none;'>&nbsp;</td>\n"
                html += "      <td style='padding: 8px; border: none;'>&nbsp;</td>\n"
                html += "    </tr>\n"
            
            # Add section header
            html += f"    <tr>\n"
            html += f"      <td colspan='2' style='padding: 8px; font-weight: bold; background-color: #e0e0e0;'>{section_name}</td>\n"
            html += f"    </tr>\n"
            
            # Add parameters in this section
            for key, value in sections[section_name]:
                html += f"    <tr>\n"
                html += f"      <td style='padding: 8px;'>{key}</td>\n"
                html += f"      <td style='padding: 8px;'>{value}</td>\n"
                html += f"    </tr>\n"
                
            first_section = False
        
        html += "  </tbody>\n"
        html += "</table>"
        
        return html