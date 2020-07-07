"""
Tag to load a smart paginator that does not iterate over every page but has
ellipses to truncate pages outside an adjacency
"""
from django import template

register = template.Library()


@register.inclusion_tag('base/paginator.html', takes_context=True)
def paginator(context, request, adjacent_pages=2):
    """
    Adds pagination context variables for use in displaying first, adjacent and
    last page links.
    """
    page_obj = context['page_obj']
    num_pages = context['paginator'].num_pages

    # Widen the adjacency if near the start or near the end of the page set
    start_page = max(page_obj.number - adjacent_pages, 1)
    if start_page <= 3:
        start_page = 1

    end_page = page_obj.number + adjacent_pages + 1
    if end_page >= num_pages - 1:
        end_page = num_pages + 1

    # Generate a list of pages to include in the paginator template
    page_numbers = [n for n in range(start_page, end_page) if 0 < n <= num_pages]

    return {
        'page_obj': page_obj,
        'paginator': context['paginator'],
        'page_numbers': page_numbers,
        'show_first': 1 not in page_numbers,
        'show_last': num_pages not in page_numbers,
        'request': request
    }
