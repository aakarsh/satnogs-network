"""SatNOGS Network Auth0 login app config"""
from django.apps import AppConfig


class Auth0LoginConfig(AppConfig):
    """Set the name of the django app for auth0login"""
    name = 'auth0login'
