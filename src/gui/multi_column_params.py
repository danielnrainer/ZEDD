"""
Multi-column measurement parameters widget for CIF import support.

This widget allows users to:
- Add/remove measurement parameters dynamically
- Import parameters from one or more CIF files
- Display parameters in a table with a column for each CIF file
- Format them as an HTML table for Zenodo deposition
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLineEdit, QPushButton, QLabel, QScrollArea, QFrame, QComboBox,
    QTextEdit, QTabWidget, QTextBrowser, QFileDialog, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QSizePolicy, QMenu
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import os

from .widgets import QCollapsibleBox


class MultiColumnParametersWidget(QWidget):
    """
    Widget for managing measurement parameters with support for multiple CIF files.
    
    Each CIF file gets its own column in the table, making it easy to compare
    and document multiple crystal structures from a single deposition.
    """
    
    parameters_changed = pyqtSignal()  # Emitted when parameters change
    
    def __init__(self):
        super().__init__()
        self.cif_columns: List[str] = []  # List of CIF filenames (column headers)
        self.parameter_rows: List[str] = []  # List of parameter names (row headers)
        self.section_assignments: Dict[str, str] = {}  # parameter_name -> section
        self.init_ui()
        
        # Add some default parameters
        self.add_default_parameters()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header with buttons
        header_layout = QHBoxLayout()
        header_label = QLabel("Measurement Parameters:")
        header_label.setStyleSheet("font-weight: bold;")
        
        self.import_cif_btn = QPushButton("📂 Import from CIF...")
        self.import_cif_btn.setToolTip("Import parameters from one or more CIF files")
        self.import_cif_btn.clicked.connect(self.import_from_cif)
        
        self.add_row_btn = QPushButton("➕ Add Row")
        self.add_row_btn.setToolTip("Add a new parameter row")
        self.add_row_btn.clicked.connect(self.add_parameter_row)
        
        self.add_column_btn = QPushButton("➕ Add Column")
        self.add_column_btn.setToolTip("Add a new value column (e.g., for another crystal)")
        self.add_column_btn.clicked.connect(lambda: self.add_column("Crystal"))
        
        self.clear_btn = QPushButton("🗑️ Clear All")
        self.clear_btn.setToolTip("Clear all parameters")
        self.clear_btn.clicked.connect(lambda: self.clear_parameters(confirm=True))
        
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(self.import_cif_btn)
        header_layout.addWidget(self.add_row_btn)
        header_layout.addWidget(self.add_column_btn)
        header_layout.addWidget(self.clear_btn)
        
        layout.addLayout(header_layout)
        
        # Main table
        self.table = QTableWidget()
        self.table.setMinimumHeight(200)
        self.table.setMaximumHeight(300)
        self.table.setAlternatingRowColors(True)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.cellChanged.connect(self.on_cell_changed)
        
        # Configure table headers
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        
        layout.addWidget(self.table)
        
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
        
        preview_content_layout.addLayout(preview_header)
        
        # Tabbed preview (rendered and source)
        self.preview_tabs = QTabWidget()
        
        # Rendered HTML tab
        self.rendered_view = QTextBrowser()
        self.rendered_view.setMaximumHeight(300)
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
        
        # Initialize table with default structure
        self._rebuild_table()
    
    def add_default_parameters(self):
        """Add common measurement parameters with suggested sections"""
        defaults = [
            # General
            ("Collection site", "General"),
            ("Sample label(s)", "General"),
            ("Crystal structure deposit", "General"),
            # Instrumental
            ("Instrument", "Instrumental"),
            ("Radiation source", "Instrumental"),
            ("Accelerating voltage [kV]", "Instrumental"),
            ("Wavelength [Å]", "Instrumental"),
            ("Probe type", "Instrumental"),
            ("Beam convergence", "Instrumental"),
            ("Detector", "Instrumental"),
            ("Number of pixels", "Instrumental"),
            ("Pixel size [µm]", "Instrumental"),
            ("Hardware binning", "Instrumental"),
            # Sample description
            ("Name", "Sample description"),
            ("Chemical composition", "Sample description"),
            ("Sample source", "Sample description"),
            ("Grid", "Sample description"),
            ("Sample preparation", "Sample description"),
            ("Sample holder", "Sample description"),
            # Experimental
            ("Data type", "Experimental"),
            ("Data collection method", "Experimental"),
            ("Collection temperature [K]", "Experimental"),
            # Software & Files
            ("Software for data collection", "Software & Files"),
            ("Software for data processing", "Software & Files"),
            ("Image folders", "Software & Files"),
            ("Image format", "Software & Files"),
        ]
        
        for name, section in defaults:
            self.parameter_rows.append(name)
            self.section_assignments[name] = section
        
        # Add one default column
        self.cif_columns.append("")
        
        self._rebuild_table()
    
    def _rebuild_table(self):
        """Rebuild the table based on current rows and columns"""
        self.table.blockSignals(True)
        
        # Calculate column count: Section + Parameter + value columns
        num_value_cols = max(1, len(self.cif_columns))
        total_cols = 2 + num_value_cols  # Section, Parameter, Values...
        
        self.table.setColumnCount(total_cols)
        self.table.setRowCount(len(self.parameter_rows))
        
        # Set headers
        headers = ["Section", "Parameter"] + self.cif_columns
        self.table.setHorizontalHeaderLabels(headers)
        
        # Set column widths
        self.table.setColumnWidth(0, 120)  # Section
        self.table.setColumnWidth(1, 180)  # Parameter
        for i in range(2, total_cols):
            self.table.setColumnWidth(i, 200)  # Value columns
        
        # Populate rows
        for row_idx, param_name in enumerate(self.parameter_rows):
            section = self.section_assignments.get(param_name, "General")
            
            # Section column (combo box)
            section_combo = self._create_section_combo(section)
            section_combo.currentTextChanged.connect(
                lambda text, r=row_idx: self._on_section_changed(r, text)
            )
            self.table.setCellWidget(row_idx, 0, section_combo)
            
            # Parameter name column
            param_item = QTableWidgetItem(param_name)
            self.table.setItem(row_idx, 1, param_item)
            
            # Value columns (initialize empty)
            for col_idx in range(2, total_cols):
                value_item = QTableWidgetItem("")
                self.table.setItem(row_idx, col_idx, value_item)
        
        self.table.blockSignals(False)
        self.update_preview()
    
    def _create_section_combo(self, current_section: str) -> QComboBox:
        """Create a section combo box"""
        combo = QComboBox()
        sections = [
            "General",
            "Instrumental",
            "Sample description",
            "Experimental",
            "Software & Files"
        ]
        combo.addItems(sections)
        combo.setCurrentText(current_section)
        return combo
    
    def _on_section_changed(self, row: int, section: str):
        """Handle section change for a row"""
        if row < len(self.parameter_rows):
            param_name = self.parameter_rows[row]
            self.section_assignments[param_name] = section
            self.update_preview()
    
    def on_cell_changed(self, row: int, col: int):
        """Handle cell content change"""
        if col == 1:  # Parameter name changed
            item = self.table.item(row, col)
            if item and row < len(self.parameter_rows):
                old_name = self.parameter_rows[row]
                new_name = item.text().strip()
                if new_name and new_name != old_name:
                    self.parameter_rows[row] = new_name
                    # Preserve section assignment
                    if old_name in self.section_assignments:
                        self.section_assignments[new_name] = self.section_assignments.pop(old_name)
        
        self.update_preview()
        self.parameters_changed.emit()
    
    def add_parameter_row(self, name: str = "", section: str = "General", values: Optional[List[str]] = None):
        """Add a new parameter row"""
        if not name:
            name = f"Parameter {len(self.parameter_rows) + 1}"
        
        # Check if parameter already exists
        if name in self.parameter_rows:
            # Find existing row and update values
            row_idx = self.parameter_rows.index(name)
            if values:
                for col_idx, value in enumerate(values):
                    if col_idx + 2 < self.table.columnCount():
                        item = self.table.item(row_idx, col_idx + 2)
                        if item:
                            item.setText(value)
            return
        
        self.parameter_rows.append(name)
        self.section_assignments[name] = section
        
        # Add row to table
        row_idx = self.table.rowCount()
        self.table.insertRow(row_idx)
        
        # Section combo
        section_combo = self._create_section_combo(section)
        section_combo.currentTextChanged.connect(
            lambda text, r=row_idx: self._on_section_changed(r, text)
        )
        self.table.setCellWidget(row_idx, 0, section_combo)
        
        # Parameter name
        param_item = QTableWidgetItem(name)
        self.table.setItem(row_idx, 1, param_item)
        
        # Value columns
        values = values or []
        for col_idx in range(2, self.table.columnCount()):
            value = values[col_idx - 2] if col_idx - 2 < len(values) else ""
            value_item = QTableWidgetItem(value)
            self.table.setItem(row_idx, col_idx, value_item)
        
        self.update_preview()
        self.parameters_changed.emit()
    
    def add_column(self, name: str, values: Optional[Dict[str, str]] = None):
        """
        Add a new value column (e.g., for another CIF file)
        
        Args:
            name: Column header name (e.g., CIF filename)
            values: Optional dict mapping parameter names to values
        """
        # Ensure unique column name
        base_name = name
        counter = 1
        while name in self.cif_columns:
            counter += 1
            name = f"{base_name} ({counter})"
        
        self.cif_columns.append(name)
        col_idx = self.table.columnCount()
        self.table.insertColumn(col_idx)
        self.table.setHorizontalHeaderItem(col_idx, QTableWidgetItem(name))
        self.table.setColumnWidth(col_idx, 200)
        
        # Populate column with values if provided
        values = values or {}
        for row_idx, param_name in enumerate(self.parameter_rows):
            value = values.get(param_name, "")
            value_item = QTableWidgetItem(value)
            self.table.setItem(row_idx, col_idx, value_item)
        
        self.update_preview()
        self.parameters_changed.emit()
    
    def remove_row(self, row: int):
        """Remove a parameter row"""
        if row < 0 or row >= len(self.parameter_rows):
            return
        
        param_name = self.parameter_rows.pop(row)
        self.section_assignments.pop(param_name, None)
        self.table.removeRow(row)
        
        self.update_preview()
        self.parameters_changed.emit()
    
    def remove_column(self, col: int):
        """Remove a value column"""
        if col < 2 or col >= self.table.columnCount():
            return  # Don't remove Section or Parameter columns
        
        col_name = self.cif_columns[col - 2]
        self.cif_columns.remove(col_name)
        self.table.removeColumn(col)
        
        self.update_preview()
        self.parameters_changed.emit()
    
    def show_context_menu(self, position):
        """Show context menu for table operations"""
        menu = QMenu(self)
        
        # Get clicked cell
        row = self.table.rowAt(position.y())
        col = self.table.columnAt(position.x())
        
        if row >= 0:
            remove_row_action = menu.addAction("🗑️ Remove Row")
            remove_row_action.triggered.connect(lambda: self.remove_row(row))
        
        if col >= 2:  # Value column
            remove_col_action = menu.addAction("🗑️ Remove Column")
            remove_col_action.triggered.connect(lambda: self.remove_column(col))
        
        menu.addSeparator()
        
        add_row_action = menu.addAction("➕ Add Row")
        add_row_action.triggered.connect(self.add_parameter_row)
        
        add_col_action = menu.addAction("➕ Add Column")
        add_col_action.triggered.connect(lambda: self.add_column(""))
        
        menu.exec(self.table.viewport().mapToGlobal(position))
    
    def import_from_cif(self):
        """Import parameters from one or more CIF files.
        
        Only populates values for parameters that already exist in the table
        (as defined by the template). CIF fields not matching existing parameters
        are silently ignored to keep the table structure consistent with the template.
        """
        from ..services.cif_parser import CIFParser, extract_parameters_from_cif
        
        filepaths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select CIF Files",
            "",
            "CIF Files (*.cif *.mcif);;All Files (*)"
        )
        
        if not filepaths:
            return
        
        parser = CIFParser()
        imported_count = 0
        
        for filepath in filepaths:
            try:
                cif_data = parser.parse_file(filepath)
                parameters = extract_parameters_from_cif(cif_data)
                
                # Create column name from filename
                filename = Path(filepath).stem
                
                # Collect values for this CIF - only for parameters already in the table
                values_dict = {}
                for param_name, (value, section) in parameters.items():
                    # Only include if parameter already exists in table
                    if param_name in self.parameter_rows:
                        values_dict[param_name] = value
                
                # Add column with values
                self.add_column(filename, values_dict)
                imported_count += 1
                
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Import Error",
                    f"Failed to import {Path(filepath).name}:\n{str(e)}"
                )
        
        if imported_count > 0:
            QMessageBox.information(
                self,
                "Import Complete",
                f"Successfully imported {imported_count} CIF file(s).\n"
                f"New columns have been added for each file."
            )
        
        self.update_preview()
    
    def get_parameters(self) -> Dict[str, str]:
        """
        Get all parameters as a dictionary (for backward compatibility).
        
        If there are multiple columns, returns the first non-empty value for each parameter.
        """
        params = {}
        for row_idx, param_name in enumerate(self.parameter_rows):
            # Get first non-empty value
            for col_idx in range(2, self.table.columnCount()):
                item = self.table.item(row_idx, col_idx)
                if item and item.text().strip():
                    params[param_name] = item.text().strip()
                    break
        return params
    
    def get_all_parameters(self) -> Dict[str, Dict[str, str]]:
        """
        Get all parameters organized by column.
        
        Returns:
            Dict mapping column names to {parameter_name: value} dicts
        """
        result = {}
        for col_idx, col_name in enumerate(self.cif_columns):
            col_params = {}
            for row_idx, param_name in enumerate(self.parameter_rows):
                item = self.table.item(row_idx, col_idx + 2)
                if item and item.text().strip():
                    col_params[param_name] = item.text().strip()
            result[col_name] = col_params
        return result
    
    def get_parameters_with_sections(self) -> Dict[str, List[Tuple[str, List[str]]]]:
        """
        Get parameters organized by sections with all column values.
        
        Returns:
            Dict mapping section names to lists of (parameter_name, [values]) tuples
        """
        sections = {}
        for row_idx, param_name in enumerate(self.parameter_rows):
            section = self.section_assignments.get(param_name, "General")
            
            # Collect values from all columns
            values = []
            has_value = False
            for col_idx in range(2, self.table.columnCount()):
                item = self.table.item(row_idx, col_idx)
                value = item.text().strip() if item else ""
                values.append(value)
                if value:
                    has_value = True
            
            if has_value:  # Only include rows with at least one value
                if section not in sections:
                    sections[section] = []
                sections[section].append((param_name, values))
        
        return sections
    
    def set_parameters(self, params: Dict[str, str]):
        """Set parameters from a dictionary (for backward compatibility)"""
        # Clear existing
        self.parameter_rows.clear()
        self.section_assignments.clear()
        self.cif_columns = ["Value"]
        
        # Add parameters from dict
        from .template_loader import _get_smart_section
        
        for key, value in params.items():
            self.parameter_rows.append(key)
            self.section_assignments[key] = _get_smart_section(key)
        
        self._rebuild_table()
        
        # Set values
        for row_idx, param_name in enumerate(self.parameter_rows):
            value = params.get(param_name, "")
            item = self.table.item(row_idx, 2)
            if item:
                item.setText(value)
    
    def clear_parameters(self, confirm: bool = False):
        """
        Clear all parameters and reset to defaults.
        
        Args:
            confirm: If True, ask for user confirmation before clearing
        """
        if confirm:
            reply = QMessageBox.question(
                self,
                "Clear Parameters",
                "Are you sure you want to clear all parameters?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        self.parameter_rows.clear()
        self.section_assignments.clear()
        self.cif_columns.clear()
        self.add_default_parameters()
    
    def update_preview(self):
        """Update the HTML preview with both rendered and source views"""
        html_table = self.generate_html_table()
        
        if not html_table:
            self.rendered_view.setHtml(
                "<p><em>No parameters to display. Add some parameters above "
                "or import from CIF files.</em></p>"
            )
            self.source_view.setPlainText("<!-- No parameters to display -->")
            return
        
        self.rendered_view.setHtml(html_table)
        formatted_html = self._format_html_source(html_table)
        self.source_view.setPlainText(formatted_html)
    
    def _format_html_source(self, html: str) -> str:
        """Format HTML source for better readability"""
        if not html:
            return ""
        
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
        
        lines = [line.strip() for line in formatted.split('\n') if line.strip()]
        return '\n'.join(lines)
    
    def copy_html_to_clipboard(self):
        """Copy HTML source to clipboard"""
        html_table = self.generate_html_table()
        if html_table:
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(html_table)
            
            original_text = self.copy_html_btn.text()
            self.copy_html_btn.setText("✅ Copied!")
            QTimer.singleShot(2000, lambda: self.copy_html_btn.setText(original_text))
    
    def generate_html_table(self) -> str:
        """Generate HTML table for Zenodo with sections and multiple columns"""
        sections = self.get_parameters_with_sections()
        
        if not sections:
            return ""
        
        num_value_cols = max(1, len(self.cif_columns))
        total_cols = 1 + num_value_cols  # Parameter + value columns
        
        html = '<table border="1" style="border-collapse: collapse; width: 100%;">\n'
        
        # Add header row if multiple columns
        if num_value_cols > 1:
            html += '  <thead>\n    <tr>\n'
            html += '      <th style="padding: 8px; background-color: #f0f0f0;">Parameter</th>\n'
            for col_name in self.cif_columns:
                html += f'      <th style="padding: 8px; background-color: #f0f0f0;">{col_name}</th>\n'
            html += '    </tr>\n  </thead>\n'
        
        html += '  <tbody>\n'
        
        # Sort sections for consistent ordering
        section_order = ["General", "Instrumental", "Sample description", "Experimental", "Software & Files"]
        ordered_sections = [s for s in section_order if s in sections]
        for s in sections:
            if s not in ordered_sections:
                ordered_sections.append(s)
        
        first_section = True
        for section_name in ordered_sections:
            if section_name not in sections:
                continue
            
            # Add empty row for spacing between sections
            if not first_section:
                html += '    <tr>\n'
                for _ in range(total_cols):
                    html += '      <td style="padding: 8px; border: none;">&nbsp;</td>\n'
                html += '    </tr>\n'
            
            # Add section header
            html += f'    <tr>\n'
            html += f'      <td colspan="{total_cols}" style="padding: 8px; font-weight: bold; background-color: #e0e0e0;"><strong>{section_name}</strong></td>\n'
            html += f'    </tr>\n'
            
            # Add parameters in this section
            for param_name, values in sections[section_name]:
                html += '    <tr>\n'
                html += f'      <td style="padding: 8px;">{param_name}</td>\n'
                
                for value in values:
                    # Convert newlines to HTML breaks
                    formatted_value = value.replace('\n', '<br>') if value else ''
                    html += f'      <td style="padding: 8px;">{formatted_value}</td>\n'
                
                html += '    </tr>\n'
            
            first_section = False
        
        html += '  </tbody>\n</table>'
        
        return html
    
    # Backward compatibility methods
    def add_parameter(self, key: str = "", value: str = "", section: str = ""):
        """Add a parameter (backward compatible method)"""
        if not section:
            from .template_loader import _get_smart_section
            section = _get_smart_section(key) if key else "General"
        
        self.add_parameter_row(key, section, [value] if value else None)
