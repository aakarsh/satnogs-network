"""Base Django URL mapping for SatNOGS Network"""
from allauth import urls as allauth_urls
from avatar import urls as avatar_urls
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.views.static import serve

from network.api.urls import API_URLPATTERNS
from network.base.urls import BASE_URLPATTERNS
from network.users.urls import USERS_URLPATTERNS

urlpatterns = [
    # Base urls
    url(r'^', include(BASE_URLPATTERNS)),
    url(r'^admin/', admin.site.urls),
    url(r'^users/', include(USERS_URLPATTERNS)),
    url(r'^accounts/', include(allauth_urls)),
    url(r'^avatar/', include(avatar_urls)),
    url(r'^api/', include(API_URLPATTERNS))
]

# Auth0
if settings.AUTH0:
    urlpatterns += [url(r'^', include('auth0login.urls'))]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [url(r'^__debug__/', include(debug_toolbar.urls))] + urlpatterns

    urlpatterns += [
        url(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
