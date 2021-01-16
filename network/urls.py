"""Base Django URL mapping for SatNOGS Network"""
from allauth import urls as allauth_urls
from avatar import urls as avatar_urls
from django.conf import settings
from django.conf.urls import include
from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve

from network.api.urls import API_URLPATTERNS
from network.base.urls import BASE_URLPATTERNS
from network.users.urls import USERS_URLPATTERNS

urlpatterns = [
    # Base urls
    path('', include(BASE_URLPATTERNS)),
    path('admin/', admin.site.urls),
    path('users/', include(USERS_URLPATTERNS)),
    path('accounts/', include(allauth_urls)),
    path('avatar/', include(avatar_urls)),
    path('api/', include(API_URLPATTERNS))
]

# Auth0
if settings.AUTH0:
    urlpatterns += [path('', include('auth0login.urls'))]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns

    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
