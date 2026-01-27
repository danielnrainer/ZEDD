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
        for key, param_data in template.ed_parameters.parameters.items():
            # Handle both new [value, section] format and old string-only format
            if isinstance(param_data, list) and len(param_data) >= 2:
                value, section = param_data[0], param_data[1]
            else:
                # Old format: just a string value, use smart section assignment
                value = param_data if param_data else ""
                section = _get_smart_section(key)
            gui_app.measurement_params_widget.add_parameter(key, value, section)
        
        # Creators - create widgets without triggering add/remove logic
        _populate_creators(gui_app, template.creators)
        
        # Contributors - create widgets without triggering add/remove logic
        _populate_contributors(gui_app, template.contributors)
        
        # Funding - DISABLED: Skip funding population since funding UI is disabled
        # _populate_funding(gui_app, template.grants)
        if template.grants:
            print(f"Note: Template contains {len(template.grants)} funding entries, but funding is disabled. Add manually on Zenodo.")
        
        # Communities - create widgets without triggering searches
        _populate_communities(gui_app, template.communities)
        
    finally:
        # Re-enable updates
        gui_app.setUpdatesEnabled(True)


def _clear_dynamic_content(gui_app) -> None:
    """Clear all dynamic content (creators, contributors, funding, communities)"""
    # Clear creators
    for widget in gui_app.creators_list[:]:
        container = widget.parent()
        if container:
            container.setParent(None)
            container.deleteLater()
    gui_app.creators_list.clear()
    
    # Clear contributors
    for widget in gui_app.contributors_list[:]:
        container = widget.parent()
        if container:
            container.setParent(None)
            container.deleteLater()
    gui_app.contributors_list.clear()
    
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


def _populate_creators(gui_app, creators) -> None:
    """Populate creator widgets from template data"""
    from ..gui.widgets import CreatorWidget
    from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QWidget
    
    # Ensure we have at least one creator
    if not creators:
        creators = [type('Creator', (), {'name': '', 'affiliation': '', 'orcid': ''})()]
    
    for creator_data in creators:
        # Create creator widget
        creator_widget = CreatorWidget()
        
        # Set data directly (this doesn't trigger signals)
        creator_widget.name_edit.setText(getattr(creator_data, 'name', ''))
        creator_widget.affiliation_edit.setText(getattr(creator_data, 'affiliation', ''))
        creator_widget.orcid_edit.setText(getattr(creator_data, 'orcid', ''))
        # Note: type_edit field commented out - only for future Contributors support
        # creator_widget.type_edit.setText(getattr(creator_data, 'type', ''))
        
        # Create container with remove button
        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.addWidget(creator_widget)
        
        remove_layout = QHBoxLayout()
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda checked, w=creator_widget, l=remove_layout: gui_app.remove_creator(w, l))
        
        remove_layout.addStretch()
        remove_layout.addWidget(remove_btn)
        container_layout.addLayout(remove_layout)
        container.setLayout(container_layout)
        
        # Add to GUI
        gui_app.creators_list.append(creator_widget)
        gui_app.creators_widget_layout.addWidget(container)
        
        # Hide remove button if only one creator
        if len(gui_app.creators_list) == 1:
            remove_btn.hide()


def _populate_contributors(gui_app, contributors) -> None:
    """Populate contributor widgets from template data"""
    from ..gui.widgets import ContributorWidget
    from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QWidget
    
    # Contributors are optional, so only add if we have data
    for contributor_data in contributors:
        # Create contributor widget
        contributor_widget = ContributorWidget()
        
        # Set data directly (this doesn't trigger signals)
        contributor_widget.name_edit.setText(getattr(contributor_data, 'name', ''))
        contributor_widget.affiliation_edit.setText(getattr(contributor_data, 'affiliation', ''))
        contributor_widget.orcid_edit.setText(getattr(contributor_data, 'orcid', ''))
        
        # Set contributor type
        contributor_type = getattr(contributor_data, 'type', '')
        if contributor_type:
            type_index = contributor_widget.type_combo.findText(contributor_type)
            if type_index >= 0:
                contributor_widget.type_combo.setCurrentIndex(type_index)
        
        # Create container with remove button
        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.addWidget(contributor_widget)
        
        remove_layout = QHBoxLayout()
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda checked, w=contributor_widget, l=remove_layout: gui_app.remove_contributor(w, l))
        
        remove_layout.addStretch()
        remove_layout.addWidget(remove_btn)
        container_layout.addLayout(remove_layout)
        container.setLayout(container_layout)
        
        # Add to GUI
        gui_app.contributors_list.append(contributor_widget)
        gui_app.contributors_widget_layout.addWidget(container)


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
        
        url_edit = QLineEdit()
        url_edit.setText(getattr(grant_data, 'url', ''))
        
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda checked, c=container: gui_app.remove_funding(c))
        
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
    
    # Software & Files parameters (check first for priority)
    software_keywords = [
        'software for data collection', 'software for data processing', 'software for',
        'crystalispro', 'data processing software', 'collection software',
        'software', 'processing', 'image', 'file', 'files', 'format', 'program'
    ]

    # Experimental parameters
    experimental_keywords = [
        'data type', 'data collection method', 'temperature', 'rotation',
        'exposure time', 'frames', 'resolution', 'completeness', 'multiplicity',
        'crystal system', 'space group', 'unit cell', 'method',
    ]
    
    # Check other categories
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
    
    # Check Software & Files first (highest priority for software-related terms)
    for keyword in software_keywords:
        if keyword in param_lower:
            return "Software & Files"
        
    # Default to General if no match
    return "General"