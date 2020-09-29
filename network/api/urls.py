"""SatNOGS Network django rest framework API url routings"""
from rest_framework import routers

from network.api import views

ROUTER = routers.DefaultRouter()

ROUTER.register(r'jobs', views.JobView, basename='jobs')
ROUTER.register(r'observations', views.ObservationView, basename='observations')
ROUTER.register(r'stations', views.StationView, basename='stations')
ROUTER.register(r'transmitters', views.TransmitterView, basename='transmitters')

API_URLPATTERNS = ROUTER.urls
