"""Tag to replace field in GET request"""
from django import template

register = template.Library()


@register.simple_tag
def url_replace(request, field, value):
    """
    Replaces a get parameter of a request's GET dict so you can keep
    everything but just change one thing. Useful for changing
    ?stuff=stuff&page=1 to ?stuff=stuff&page=2
    """
    dict_ = request.GET.copy()

    dict_[field] = value

    return dict_.urlencode()
