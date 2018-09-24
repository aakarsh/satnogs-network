import csv
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.contrib.admin.helpers import label_for_field


def export_as_csv(modeladmin, request, queryset):
    """
    Generic csv export admin action.
    based on http://djangosnippets.org/snippets/1697/ and /2020/
    """
    if not request.user.is_staff:
        raise PermissionDenied
    opts = modeladmin.model._meta
    field_names = modeladmin.list_display
    if 'action_checkbox' in field_names:
        field_names.remove('action_checkbox')

    response = HttpResponse(content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename=%s.csv' % unicode(opts)\
                                      .replace('.', '_')

    writer = csv.writer(response)
    headers = []
    for field_name in list(field_names):
        label = label_for_field(field_name, modeladmin.model, modeladmin)
        if label.islower():
            label = label.title()
        headers.append(label)
    writer.writerow(headers)
    for row in queryset:
        values = []
        for field in field_names:
            try:
                value = (getattr(row, field))
            except AttributeError:
                value = (getattr(modeladmin, field))
            if callable(value):
                try:
                    # get value from model
                    value = value()
                except Exception:
                    # get value from modeladmin e.g: admin_method_1
                    value = value(row)
            if value is None:
                value = ''
            values.append(unicode(value).encode('utf-8'))
        writer.writerow(values)
    return response
