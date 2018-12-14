from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.views.static import serve

from avatar import urls as avatar_urls
from allauth import urls as allauth_urls

from network.base.urls import base_urlpatterns
from network.users.urls import users_urlpatterns
from network.api.urls import api_urlpatterns

handler404 = 'network.base.views.custom_404'
handler500 = 'network.base.views.custom_500'

urlpatterns = [
    # Base urls
    url(r'^', include(base_urlpatterns)),

    url(r'^admin/', admin.site.urls),
    url(r'^users/', include(users_urlpatterns)),
    url(r'^accounts/', include(allauth_urls)),
    url(r'^avatar/', include(avatar_urls)),

    url(r'^api/', include(api_urlpatterns))
]

# Auth0
if settings.AUTH0:
    urlpatterns += [
        url(r'^', include('auth0login.urls'))
    ]

if settings.DEBUG:
    urlpatterns += [
        url(r'^media/(?P<path>.*)$', serve,
            {'document_root': settings.MEDIA_ROOT}),
    ]
