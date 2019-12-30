#!/usr/bin/env python
"""WSGI module for SatNOGS Network"""
from __future__ import absolute_import

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network.settings')

application = get_wsgi_application()
