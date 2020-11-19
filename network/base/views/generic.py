"""Django base views for SatNOGS Network"""
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from network.base.decorators import staff_required
from network.base.tasks import fetch_data, update_future_observations_with_new_tle_sets


def index(request):
    """View to render index page."""
    return render(
        request, 'base/home.html', {
            'mapbox_id': settings.MAPBOX_MAP_ID,
            'mapbox_token': settings.MAPBOX_TOKEN
        }
    )


def robots(request):
    """Returns response for robots.txt requests"""
    data = render(request, 'robots.txt', {'environment': settings.ENVIRONMENT})
    response = HttpResponse(data, content_type='text/plain; charset=utf-8')
    return response


@staff_required
def settings_site(request):
    """View to render settings page."""
    if request.method == 'POST':
        fetch_data.delay()
        update_future_observations_with_new_tle_sets.delay()
        messages.success(request, 'Data fetching task was triggered successfully!')
        return redirect(reverse('users:view_user', kwargs={"username": request.user.username}))
    return render(request, 'base/settings_site.html')
