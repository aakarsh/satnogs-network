#!/usr/bin/env python
"""WSGI module for SatNOGS Network"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network.settings')

application = get_wsgi_application()
