"""Django template tags for SatNOGS Network"""
from django import template
from django.core.urlresolvers import reverse

register = template.Library()


@register.simple_tag
def active(request, urls):
    """Returns if this is an active URL"""
    if request.path in (reverse(url) for url in urls.split()):
        return 'active'
    return None


@register.simple_tag
def drifted_frq(frq, drift):
    """Returns drifred frequency"""
    return int(round(frq + ((frq * drift) / float(pow(10, 9)))))


@register.filter
def frq(value):
    """Returns Hz formatted frequency html string"""
    try:
        to_format = float(value)
    except (TypeError, ValueError):
        return '-'
    formatted = format(float(to_format) / 1000000, '.3f')
    formatted = formatted + ' MHz'
    return formatted


@register.filter
def percentagerest(value):
    """Returns the rest of percentage from a given (percentage) value"""
    try:
        return 100 - value
    except (TypeError, ValueError):
        return 0


@register.filter
def get_count_from_id(dictionary, key):
    """Returns observations count from dictionary"""
    if key in dictionary.keys():
        return dictionary[key]
    return 0


@register.filter
def sortdemoddata(demoddata):
    """Returns a date sorted list of DemodData"""
    try:
        return sorted(list(demoddata), key=lambda x: str(x.payload_demod).split('/', 2)[2:])
    except (TypeError, ValueError):
        return demoddata
