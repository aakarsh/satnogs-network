"""Django users URL routings for SatNOGS Network"""
from django.urls import path, re_path

from network.users import views

USERS_URLPATTERNS = (
    [
        path('redirect/', views.UserRedirectView.as_view(), name='redirect_user'),
        path('update/', views.UserUpdateView.as_view(), name='update_user'),
        re_path(r'^(?P<username>[\w.@+-]+)/$', views.view_user, name='view_user'),
    ], 'users'
)
