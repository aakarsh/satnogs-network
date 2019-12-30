"""SatNOGS Network base decorators"""
from __future__ import absolute_import

from django.core.urlresolvers import reverse
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect


def admin_required(function):
    """Decorator for requiring admin permission"""
    def wrap(request, *args, **kwargs):
        """Wrap function of decorator"""
        if not request.user.is_authenticated():
            return redirect(reverse('account_login'))
        if request.user.is_superuser:
            return function(request, *args, **kwargs)
        return redirect(reverse('base:home'))

    return wrap


def ajax_required(function):
    """Decorator for requiring request to be and ajax one"""
    def wrap(request, *args, **kwargs):
        """Wrap function of decorator"""
        if not request.is_ajax():
            return HttpResponseBadRequest()
        return function(request, *args, **kwargs)

    return wrap
