"""
GUI interface module
"""

from .widgets import QCollapsibleBox, AuthorWidget
from .upload_worker import ModularUploadWorker
from .app import ZenodoUploaderApp

__all__ = ['QCollapsibleBox', 'ModularUploadWorker', 'AuthorWidget', 'ZenodoUploaderApp']
