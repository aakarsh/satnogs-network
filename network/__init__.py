from __future__ import absolute_import

from .celery import app as celery_app  # noqa


__all__ = ['celery_app']

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
