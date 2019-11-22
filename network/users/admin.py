"""Define functions and settings for the django admin users interface"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.db.models import Count

from network.users.models import User


class HasStationListFilter(admin.SimpleListFilter):
    """Filter users by checking if the own a station or not"""
    title = 'having station'
    parameter_name = 'has_station'

    def lookups(self, request, model_admin):
        return (
            (1, 'Yes'),
            (0, 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.annotate(count=Count('ground_stations')).filter(count__gt=0)
        if self.value() == '0':
            return queryset.annotate(count=Count('ground_stations')).filter(count__lt=1)
        return None


class UserAdmin(AuthUserAdmin):
    """Class of AuthUserAdmin"""
    create_form_class = UserCreationForm
    update_form_class = UserChangeForm
    list_filter = AuthUserAdmin.list_filter + (HasStationListFilter, )


admin.site.register(User, UserAdmin)
