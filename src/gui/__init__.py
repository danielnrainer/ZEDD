"""
GUI interface module
"""

from .widgets import QCollapsibleBox, CreatorWidget, ContributorWidget
from .upload_worker import ModularUploadWorker
from .app import ZenodoUploaderApp

__all__ = ['QCollapsibleBox', 'ModularUploadWorker', 'CreatorWidget', 'ContributorWidget', 'ZenodoUploaderApp']
