"""
GUI interface module
"""

from .widgets import QCollapsibleBox, CreatorWidget, ContributorWidget
from .upload_worker import ModularUploadWorker
from .app import ZenodoUploaderApp
from .multi_column_params import MultiColumnParametersWidget

__all__ = ['QCollapsibleBox', 'ModularUploadWorker', 'CreatorWidget', 'ContributorWidget', 'ZenodoUploaderApp', 'MultiColumnParametersWidget']
