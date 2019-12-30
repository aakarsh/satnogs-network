"""SatNOGS Network django rest framework API url routings"""
from __future__ import absolute_import

from rest_framework import routers

from network.api import views

ROUTER = routers.DefaultRouter()

ROUTER.register(r'jobs', views.JobView, base_name='jobs')
ROUTER.register(r'data', views.ObservationView, base_name='data')
ROUTER.register(r'observations', views.ObservationView, base_name='observations')
ROUTER.register(r'stations', views.StationView, base_name='stations')
ROUTER.register(r'transmitters', views.TransmitterView, base_name='transmitters')

API_URLPATTERNS = ROUTER.urls
