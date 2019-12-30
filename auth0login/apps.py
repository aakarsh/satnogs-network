# -*- coding: utf-8 -*-
"""SatNOGS Network Auth0 login app config"""
from __future__ import absolute_import, unicode_literals

from django.apps import AppConfig


class Auth0LoginConfig(AppConfig):
    """Set the name of the django app for auth0login"""
    name = 'auth0login'
