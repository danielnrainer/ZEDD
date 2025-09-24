"""
Main GUI application widgets
"""

import sys
import os
import json
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QFormLayout, QGroupBox, QLineEdit, QTextEdit, QComboBox, 
    QPushButton, QFileDialog, QProgressBar, QLabel, QMessageBox,
    QListWidget, QListWidgetItem, QTabWidget, QCheckBox, QSpinBox,
    QDateEdit, QScrollArea, QFrame, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings, QDate
from PyQt6.QtGui import QFont, QPixmap, QIcon, QCursor
from PyQt6.QtCore import QPropertyAnimation, QSize

from ..services.metadata import Author, EDParameters, ZenodoMetadata

class QCollapsibleBox(QWidget):
    """A custom collapsible box widget"""
    
    def __init__(self, title="", parent=None, collapsed=False):
        super().__init__(parent)
        
        self.toggleButton = QPushButton(title)
        self.toggleButton.setStyleSheet("text-align: left; padding: 5px;")
        self.toggleButton.setCheckable(True)
        self.toggleButton.setChecked(not collapsed)  # Inverted logic: checked means expanded
        self.toggleButton.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.contentWidget = QWidget()
        self.contentWidget.setVisible(not collapsed)
        
        lay = QVBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.toggleButton)
        lay.addWidget(self.contentWidget)
        
        self.toggleButton.toggled.connect(self.toggle)
        
    def setContentLayout(self, layout):
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        self.contentWidget.setLayout(layout)
        
        self.toggleButton.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 4px;
                margin: 0px;
                border: none;
                background-color: #f0f0f0;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        
    def toggle(self, checked):
        self.contentWidget.setVisible(checked)


class AuthorWidget(QWidget):
    """Widget for entering author information"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Last, First")
        
        self.affiliation_edit = QLineEdit()
        self.affiliation_edit.setPlaceholderText("Institution")
        
        self.orcid_edit = QLineEdit()
        self.orcid_edit.setPlaceholderText("0000-0000-0000-0000")
        
        layout.addWidget(QLabel("Name:"))
        layout.addWidget(self.name_edit)
        layout.addWidget(QLabel("Affiliation:"))
        layout.addWidget(self.affiliation_edit)
        layout.addWidget(QLabel("ORCID:"))
        layout.addWidget(self.orcid_edit)
        
        self.setLayout(layout)
    
    def get_data(self) -> Dict[str, str]:
        """Get author data as dictionary"""
        data = {"name": self.name_edit.text().strip()}
        
        if self.affiliation_edit.text().strip():
            data["affiliation"] = self.affiliation_edit.text().strip()
        
        if self.orcid_edit.text().strip():
            data["orcid"] = self.orcid_edit.text().strip()
        
        return data
    
    def set_data(self, data: Dict[str, str]):
        """Set author data from dictionary"""
        self.name_edit.setText(data.get("name", ""))
        self.affiliation_edit.setText(data.get("affiliation", ""))
        self.orcid_edit.setText(data.get("orcid", ""))
        
    def clear(self):
        """Clear all input fields"""
        self.name_edit.clear()
        self.affiliation_edit.clear()
        self.orcid_edit.clear()
