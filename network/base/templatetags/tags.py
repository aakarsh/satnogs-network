"""Django template tags for SatNOGS Network"""
from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag
def active(request, urls):
    """Returns if this is an active URL"""
    if request.path in (reverse(url) for url in urls.split()):
        return 'active'
    return None


@register.simple_tag
def drifted_frq(value, drift):
    """Returns drifred frequency"""
    return int(round(value + ((value * drift) / 1e9)))


@register.filter
def sort_types(types):
    """Returns sorted 'Other' antenna types"""
    other = []
    sorted_types = []
    for antenna_type in types:
        if 'Other' in antenna_type.name:
            other.append(antenna_type)
            continue
        sorted_types.append(antenna_type)
    return sorted_types + other


@register.filter
def frq(value):
    """Returns Hz formatted frequency html string"""
    try:
        to_format = float(value)
    except (TypeError, ValueError):
        return '-'
    if to_format >= 1000000000000:
        formatted = format(to_format / 1000000000000, '.3f')
        formatted = formatted + ' THz'
    elif to_format >= 1000000000:
        formatted = format(to_format / 1000000000, '.3f')
        formatted = formatted + ' GHz'
    elif to_format >= 1000000:
        formatted = format(to_format / 1000000, '.3f')
        formatted = formatted + ' MHz'
    elif to_format >= 1000:
        formatted = format(to_format / 1000, '.3f')
        formatted = formatted + ' KHz'
    else:
        formatted = format(to_format, '.3f')
        formatted = formatted + ' Hz'
    return formatted


@register.filter
def percentagerest(value):
    """Returns the rest of percentage from a given (percentage) value"""
    try:
        return 100 - value
    except (TypeError, ValueError):
        return 0


@register.filter
def sortdemoddata(demoddata):
    """Returns a date sorted list of DemodData"""
    try:
        return sorted(list(demoddata), key=lambda x: str(x.payload_demod).split('/', 2)[2:])
    except (TypeError, ValueError):
        return demoddata


@register.filter
def lookup_with_key(dictionary, key):
    """Returns a value from dictionary for a given key"""
    return dictionary.get(key)
