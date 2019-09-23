from __future__ import absolute_import

from ._version import get_versions
from .celery import app as celery_app  # noqa

__all__ = ['celery_app']

__version__ = get_versions()['version']
del get_versions
