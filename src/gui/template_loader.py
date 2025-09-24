"""
Clean GUI template loading methods

This module provides methods to populate the GUI from template data
without triggering cascading signal handlers.
"""

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QWidget

from ..services.templates import MetadataTemplate


def populate_gui_from_template(gui_app, template: MetadataTemplate) -> None:
    """
    Populate GUI fields from template data without triggering signals
    
    Args:
        gui_app: The ZenodoUploaderApp instance
        template: MetadataTemplate to populate from
    """
    # Temporarily block all signals to prevent cascading updates
    gui_app.setUpdatesEnabled(False)
    
    try:
        # Clear existing dynamic content first
        _clear_dynamic_content(gui_app)
        
        # Basic metadata fields
        gui_app.title_edit.setText(template.title)
        gui_app.description_edit.setText(template.description)
        
        # Combo boxes
        _set_combo_by_text(gui_app.upload_type_combo, template.upload_type)
        _set_combo_by_text(gui_app.access_right_combo, template.access_right)
        _set_combo_by_data(gui_app.license_combo, template.license)
        
        # Keywords and notes
        gui_app.keywords_edit.setText(", ".join(template.keywords))
        gui_app.notes_edit.setText(template.notes)
        
        # Publication date
        if template.publication_date:
            date = QDate.fromString(template.publication_date, "yyyy-MM-dd")
            if date.isValid():
                gui_app.publication_date_edit.setDate(date)
        
        # Measurement Parameters (dynamic)
        gui_app.measurement_params_widget.clear_parameters()
        for key, value in template.ed_parameters.parameters.items():
            # Smart section assignment based on parameter names
            section = _get_smart_section(key)
            gui_app.measurement_params_widget.add_parameter(key, value, section)
        
        # Authors - create widgets without triggering add/remove logic
        _populate_authors(gui_app, template.creators)
        
        # Funding - create widgets without triggering add/remove logic
        _populate_funding(gui_app, template.grants)
        
        # Communities - create widgets without triggering searches
        _populate_communities(gui_app, template.communities)
        
    finally:
        # Re-enable updates
        gui_app.setUpdatesEnabled(True)


def _clear_dynamic_content(gui_app) -> None:
    """Clear all dynamic content (authors, funding, communities)"""
    # Clear authors
    for widget in gui_app.authors_list[:]:
        container = widget.parent()
        if container:
            container.setParent(None)
            container.deleteLater()
    gui_app.authors_list.clear()
    
    # Clear funding
    for container in gui_app.funding_list[:]:
        container.setParent(None)
        container.deleteLater()
    gui_app.funding_list.clear()
    
    # Clear communities
    for widget in gui_app.communities_list[:]:
        container = widget.parent()
        if container:
            container.setParent(None)
            container.deleteLater()
    gui_app.communities_list.clear()


def _set_combo_by_text(combo, text: str) -> None:
    """Set combo box by text value"""
    index = combo.findText(text)
    if index >= 0:
        combo.setCurrentIndex(index)


def _set_combo_by_data(combo, data: str) -> None:
    """Set combo box by data value"""
    index = combo.findData(data)
    if index >= 0:
        combo.setCurrentIndex(index)


def _populate_authors(gui_app, authors) -> None:
    """Populate author widgets from template data"""
    from ..gui.widgets import AuthorWidget
    from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QWidget
    
    # Ensure we have at least one author
    if not authors:
        authors = [type('Author', (), {'name': '', 'affiliation': '', 'orcid': ''})()]
    
    for author_data in authors:
        # Create author widget
        author_widget = AuthorWidget()
        
        # Set data directly (this doesn't trigger signals)
        author_widget.name_edit.setText(getattr(author_data, 'name', ''))
        author_widget.affiliation_edit.setText(getattr(author_data, 'affiliation', ''))
        author_widget.orcid_edit.setText(getattr(author_data, 'orcid', ''))
        
        # Create container with remove button
        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.addWidget(author_widget)
        
        remove_layout = QHBoxLayout()
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda checked, w=author_widget, l=remove_layout: gui_app.remove_author(w, l))
        
        remove_layout.addStretch()
        remove_layout.addWidget(remove_btn)
        container_layout.addLayout(remove_layout)
        container.setLayout(container_layout)
        
        # Add to GUI
        gui_app.authors_list.append(author_widget)
        gui_app.authors_widget_layout.addWidget(container)
        
        # Hide remove button if only one author
        if len(gui_app.authors_list) == 1:
            remove_btn.hide()


def _populate_funding(gui_app, grants) -> None:
    """Populate funding widgets from template data"""
    from PyQt6.QtWidgets import QWidget, QFormLayout, QLineEdit, QPushButton
    
    for grant_data in grants:
        container = QWidget()
        container_layout = QFormLayout()
        
        funder_edit = QLineEdit()
        funder_edit.setText(getattr(grant_data, 'funder', ''))
        
        award_number_edit = QLineEdit()
        award_number_edit.setText(getattr(grant_data, 'award_number', ''))
        
        award_title_edit = QLineEdit()
        award_title_edit.setText(getattr(grant_data, 'award_title', ''))
        
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda checked, c=container: gui_app.remove_funding(c))
        
        container_layout.addRow("Funder:", funder_edit)
        container_layout.addRow("Award Number:", award_number_edit)
        container_layout.addRow("Award Title:", award_title_edit)
        container_layout.addRow("", remove_btn)
        
        container.setLayout(container_layout)
        container.setProperty('funder_edit', funder_edit)
        container.setProperty('award_number_edit', award_number_edit)
        container.setProperty('award_title_edit', award_title_edit)
        
        gui_app.funding_layout.addWidget(container)
        gui_app.funding_list.append(container)
        
        # Hide remove button if only one funding entry
        if len(gui_app.funding_list) == 1:
            remove_btn.hide()


def _populate_communities(gui_app, communities) -> None:
    """Populate community widgets from template data"""
    from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton
    
    # Ensure we have at least the default community
    if not communities:
        communities = [type('Community', (), {'identifier': 'microed'})()]
    
    for community_data in communities:
        container = QWidget()
        container_layout = QHBoxLayout()
        
        community_name = QLineEdit()
        community_name.setPlaceholderText("Community identifier")
        community_name.setReadOnly(True)
        community_name.setText(getattr(community_data, 'identifier', ''))
        
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda checked, c=container, n=community_name: gui_app.remove_community(c, n))
        
        container_layout.addWidget(community_name)
        container_layout.addWidget(remove_btn)
        container.setLayout(container_layout)
        
        gui_app.communities_layout.addWidget(container)
        gui_app.communities_list.append(community_name)
        
        # Hide remove button if only one community
        if len(gui_app.communities_list) == 1:
            remove_btn.hide()


def _get_smart_section(parameter_name: str) -> str:
    """
    Automatically assign section based on parameter name
    """
    param_lower = parameter_name.lower()
    
    # General information
    general_keywords = [
        'collection site', 'sample label', 'crystal structure deposit', 
        'data availability', 'deposit', 'site', 'label'
    ]
    
    # Instrumental parameters
    instrumental_keywords = [
        'instrument', 'radiation source', 'voltage', 'wavelength', 'probe type',
        'beam', 'detector', 'pixel', 'binning', 'source', 'accelerating'
    ]
    
    # Sample description
    sample_keywords = [
        'name', 'chemical composition', 'molecular weight', 'sample source',
        'grid', 'sample preparation', 'sample holder', 'crystal size',
        'crystal morphology', 'composition', 'preparation', 'holder', 'morphology'
    ]
    
    # Experimental parameters
    experimental_keywords = [
        'data type', 'data collection method', 'temperature', 'rotation',
        'exposure time', 'frames', 'resolution', 'completeness', 'multiplicity',
        'crystal system', 'space group', 'unit cell', 'method', 'collection'
    ]
    
    # Check each category
    for keyword in general_keywords:
        if keyword in param_lower:
            return "General"
    
    for keyword in instrumental_keywords:
        if keyword in param_lower:
            return "Instrumental"
    
    for keyword in sample_keywords:
        if keyword in param_lower:
            return "Sample description"
    
    for keyword in experimental_keywords:
        if keyword in param_lower:
            return "Experimental"
    
    # Default to General if no match
    return "General"