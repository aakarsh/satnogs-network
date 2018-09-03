from django.conf.urls import url
from django.views.generic import TemplateView

from network.base import views

base_urlpatterns = ([
    url(r'^$', views.index, name='home'),
    url(r'^about/$', TemplateView.as_view(template_name='base/about.html'), name='about'),
    url(r'^robots\.txt$', views.robots, name='robots'),
    url(r'^settings_site/$', views.settings_site, name='settings_site'),

    # Observations
    url(r'^observations/$', views.ObservationListView.as_view(), name='observations_list'),
    url(r'^observations/(?P<id>[0-9]+)/$', views.observation_view,
        name='observation_view'),
    url(r'^observations/(?P<id>[0-9]+)/delete/$', views.observation_delete,
        name='observation_delete'),
    url(r'^observations/new/$', views.observation_new, name='observation_new'),
    url(r'^prediction_windows/(?P<sat_id>[\w.@+-]+)/(?P<transmitter>[\w.@+-]+)/'
        '(?P<start_date>.+)/(?P<end_date>.+)/(?P<station_id>[\w.@+-]+)/$',
        views.prediction_windows, name='prediction_windows_filtered'),
    url(r'^prediction_windows/(?P<sat_id>[\w.@+-]+)/(?P<transmitter>[\w.@+-]+)/'
        '(?P<start_date>.+)/(?P<end_date>.+)/$',
        views.prediction_windows, name='prediction_windows'),
    url(r'^pass_predictions/(?P<id>[\w.@+-]+)/$',
        views.pass_predictions, name='pass_predictions'),
    url(r'^observation_vet/(?P<id>[0-9]+)/(?P<status>[a-z]+)/$', views.observation_vet,
        name='observation_vet'),

    # Stations
    url(r'^stations/$', views.stations_list, name='stations_list'),
    url(r'^stations/(?P<id>[0-9]+)/$', views.station_view, name='station_view'),
    url(r'^stations/(?P<id>[0-9]+)/log/$', views.station_log, name='station_log'),
    url(r'^stations/(?P<id>[0-9]+)/delete/$', views.station_delete, name='station_delete'),
    url(r'^stations/edit/$', views.station_edit, name='station_edit'),
    url(r'^stations/edit/(?P<id>[0-9]+)/$', views.station_edit, name='station_edit'),
    url(r'^stations_all/$', views.StationAllView.as_view({'get': 'list'}), name='stations_all'),

    # Satellites
    url(r'^satellites/(?P<id>[0-9]+)/$', views.satellite_view, name='satellite_view'),
    url(r'^satellite_position/(?P<sat_id>[0-9]+)/$', views.satellite_position,
        name='satellite_position'),

    # Transmitters
    url(r'^transmitters/(?P<id>[0-9]+)/$', views.transmitters_view,
        name='transmitters_view'),
], 'base')
