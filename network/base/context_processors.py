"""SatNOGS Network django context processors"""
from django.conf import settings
from django.template.loader import render_to_string

from network import __version__
from network.base.stats import unknown_observations_count


def analytics(request):
    """Returns analytics code."""
    if settings.ENVIRONMENT == 'production':
        return {'analytics_code': render_to_string('includes/analytics.html')}
    return {'analytics_code': ''}


def stage_notice(request):
    """Displays stage notice."""
    if settings.ENVIRONMENT == 'stage':
        return {'stage_notice': render_to_string('includes/stage_notice.html')}
    return {'stage_notice': ''}


def user_processor(request):
    """Returns number of user's observations with unknown status."""
    if request.user.is_authenticated:
        owner_unknown_count = unknown_observations_count(request.user)
        return {'owner_unknown_count': owner_unknown_count}
    return {'owner_unknown_count': ''}


def auth_block(request):
    """Displays auth links local vs auth0."""
    if settings.AUTH0:
        return {'auth_block': render_to_string('includes/auth_auth0.html')}
    return {'auth_block': render_to_string('includes/auth_local.html')}


def logout_block(request):
    """Displays logout links local vs auth0."""
    if settings.AUTH0:
        return {'logout_block': render_to_string('includes/logout_auth0.html')}
    return {'logout_block': render_to_string('includes/logout_local.html')}


def version(request):
    """Displays the current satnogs-network version."""
    return {'version': 'Version: {}'.format(__version__)}
