"""Django base URL routings for SatNOGS Network"""
from __future__ import absolute_import

from django.conf.urls import url
from django.views.generic import TemplateView

from network.base.views import generic, observation, scheduling, station

BASE_URLPATTERNS = (
    [
        # Generic
        url(r'^$', generic.index, name='home'),
        url(r'^about/$', TemplateView.as_view(template_name='base/about.html'), name='about'),
        url(r'^robots\.txt$', generic.robots, name='robots'),
        url(r'^settings_site/$', generic.settings_site, name='settings_site'),

        # Observations
        url(
            r'^observations/$',
            observation.ObservationListView.as_view(),
            name='observations_list'
        ),
        url(
            r'^observations/(?P<observation_id>[0-9]+)/$',
            observation.observation_view,
            name='observation_view'
        ),
        url(
            r'^observations/(?P<observation_id>[0-9]+)/delete/$',
            observation.observation_delete,
            name='observation_delete'
        ),
        url(
            r'^observation_vet/(?P<observation_id>[0-9]+)/$',
            observation.observation_vet,
            name='observation_vet'
        ),
        url(
            r'^satellites/(?P<norad_id>[0-9]+)/$',
            observation.satellite_view,
            name='satellite_view'
        ),

        # Stations
        url(
            r'^stations_all/$',
            station.StationAllView.as_view({'get': 'list'}),
            name='stations_all'
        ),
        url(r'^stations/$', station.stations_list, name='stations_list'),
        url(r'^stations/(?P<station_id>[0-9]+)/$', station.station_view, name='station_view'),
        url(
            r'^stations/(?P<station_id>[0-9]+)/log/$',
            station.station_log_view,
            name='station_log'
        ),
        url(
            r'^stations/(?P<station_id>[0-9]+)/delete/$',
            station.station_delete,
            name='station_delete'
        ),
        url(
            r'^stations/(?P<station_id>[0-9]+)/delete_future_observations/$',
            station.station_delete_future_observations,
            name='station_delete_future_observations'
        ),
        url(r'^stations/edit/$', station.station_edit, name='station_edit'),
        url(r'^stations/edit/(?P<station_id>[0-9]+)/$', station.station_edit, name='station_edit'),

        # Scheduling
        url(r'^observations/new/$', scheduling.observation_new, name='observation_new'),
        url(r'^prediction_windows/$', scheduling.prediction_windows, name='prediction_windows'),
        url(
            r'^pass_predictions/(?P<station_id>[\w.@+-]+)/$',
            scheduling.pass_predictions,
            name='pass_predictions'
        ),
        url(r'^scheduling_stations/$', scheduling.scheduling_stations, name='scheduling_stations'),
        url(r'^transmitters/', scheduling.transmitters_view, name='transmitters_view'),
    ],
    'base'
)
