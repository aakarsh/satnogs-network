"""Django base URL routings for SatNOGS Network"""
from django.urls import path, re_path
from django.views.generic import TemplateView

from network.base.views import generic, observation, scheduling, station

BASE_URLPATTERNS = (
    [
        # Generic
        path('', generic.index, name='home'),
        path('about/', TemplateView.as_view(template_name='base/about.html'), name='about'),
        path('robots.txt', generic.robots, name='robots'),
        path('settings_site/', generic.settings_site, name='settings_site'),

        # Observations
        path('observations/', observation.ObservationListView.as_view(), name='observations_list'),
        re_path(
            r'^observations/(?P<observation_id>[0-9]+)/$',
            observation.observation_view,
            name='observation_view'
        ),
        re_path(
            r'^observations/(?P<observation_id>[0-9]+)/delete/$',
            observation.observation_delete,
            name='observation_delete'
        ),
        re_path(
            r'^waterfall_vet/(?P<observation_id>[0-9]+)/$',
            observation.waterfall_vet,
            name='waterfall_vet'
        ),
        re_path(
            r'^satellites/(?P<norad_id>[0-9]+)/$',
            observation.satellite_view,
            name='satellite_view'
        ),

        # Stations
        path('stations_all/', station.station_all_view, name='stations_all'),
        path('stations/', station.stations_list, name='stations_list'),
        re_path(r'^stations/(?P<station_id>[0-9]+)/$', station.station_view, name='station_view'),
        re_path(
            r'^stations/(?P<station_id>[0-9]+)/log/$',
            station.station_log_view,
            name='station_log'
        ),
        re_path(
            r'^stations/(?P<station_id>[0-9]+)/delete/$',
            station.station_delete,
            name='station_delete'
        ),
        re_path(
            r'^stations/(?P<station_id>[0-9]+)/delete_future_observations/$',
            station.station_delete_future_observations,
            name='station_delete_future_observations'
        ),
        path('stations/edit/', station.station_edit, name='station_edit'),
        re_path(
            r'^stations/edit/(?P<station_id>[0-9]+)/$', station.station_edit, name='station_edit'
        ),

        # Scheduling
        path('observations/new/', scheduling.observation_new, name='observation_new'),
        path('prediction_windows/', scheduling.prediction_windows, name='prediction_windows'),
        re_path(
            r'^pass_predictions/(?P<station_id>[\w.@+-]+)/$',
            scheduling.pass_predictions,
            name='pass_predictions'
        ),
        path('scheduling_stations/', scheduling.scheduling_stations, name='scheduling_stations'),
        path('transmitters/', scheduling.transmitters_view, name='transmitters_view'),
    ],
    'base'
)
