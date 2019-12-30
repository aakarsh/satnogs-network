"""Django users URL routings for SatNOGS Network"""
from __future__ import absolute_import

from django.conf.urls import url

from network.users import views

USERS_URLPATTERNS = (
    [
        url(r'^redirect/$', views.UserRedirectView.as_view(), name='redirect_user'),
        url(r'^update/$', views.UserUpdateView.as_view(), name='update_user'),
        url(r'^(?P<username>[\w.@+-]+)/$', views.view_user, name='view_user'),
    ], 'users'
)
