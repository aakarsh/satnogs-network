"""Django base URL routings for SatNOGS Network"""
from __future__ import absolute_import

from django.conf.urls import url
from django.views.generic import TemplateView

from network.base import views

BASE_URLPATTERNS = (
    [
        url(r'^$', views.index, name='home'),
        url(r'^about/$', TemplateView.as_view(template_name='base/about.html'), name='about'),
        url(r'^robots\.txt$', views.robots, name='robots'),
        url(r'^settings_site/$', views.settings_site, name='settings_site'),

        # Observations
        url(r'^observations/$', views.ObservationListView.as_view(), name='observations_list'),
        url(
            r'^observations/(?P<observation_id>[0-9]+)/$',
            views.observation_view,
            name='observation_view'
        ),
        url(
            r'^observations/(?P<observation_id>[0-9]+)/delete/$',
            views.observation_delete,
            name='observation_delete'
        ),
        url(r'^observations/new/$', views.observation_new, name='observation_new'),
        url(r'^prediction_windows/$', views.prediction_windows, name='prediction_windows'),
        url(
            r'^pass_predictions/(?P<station_id>[\w.@+-]+)/$',
            views.pass_predictions,
            name='pass_predictions'
        ),
        url(
            r'^observation_vet/(?P<observation_id>[0-9]+)/$',
            views.observation_vet,
            name='observation_vet'
        ),

        # Stations
        url(r'^stations/$', views.stations_list, name='stations_list'),
        url(r'^stations/(?P<station_id>[0-9]+)/$', views.station_view, name='station_view'),
        url(r'^stations/(?P<station_id>[0-9]+)/log/$', views.station_log_view, name='station_log'),
        url(
            r'^stations/(?P<station_id>[0-9]+)/delete/$',
            views.station_delete,
            name='station_delete'
        ),
        url(r'^stations/edit/$', views.station_edit, name='station_edit'),
        url(r'^stations/edit/(?P<station_id>[0-9]+)/$', views.station_edit, name='station_edit'),
        url(
            r'^stations_all/$', views.StationAllView.as_view({'get': 'list'}), name='stations_all'
        ),
        url(r'^scheduling_stations/$', views.scheduling_stations, name='scheduling_stations'),

        # Satellites
        url(r'^satellites/(?P<norad_id>[0-9]+)/$', views.satellite_view, name='satellite_view'),

        # Transmitters
        url(r'^transmitters/', views.transmitters_view, name='transmitters_view'),
    ],
    'base'
)
