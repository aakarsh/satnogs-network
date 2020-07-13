"""SatNOGS Network Auth0 login module URL routers"""
from django.conf.urls import include, url

from . import views

urlpatterns = [
    url('^$', views.index),
    url(r'^', include(('django.contrib.auth.urls', 'auth'), namespace='auth')),
    url(r'^', include(('social_django.urls', 'social'), namespace='social')),
]
