"""Define functions and settings for the django admin base interface"""
from __future__ import absolute_import

from django.conf.urls import url
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse

from network.base.models import Antenna, DemodData, Observation, Satellite, \
    Station, Tle, Transmitter
from network.base.tasks import sync_to_db
from network.base.utils import export_as_csv, export_station_status


@admin.register(Antenna)
class AntennaAdmin(admin.ModelAdmin):
    """Define Antenna view in django admin UI"""
    list_display = (
        'id',
        '__str__',
        'antenna_count',
        'station_list',
    )
    list_filter = (
        'band',
        'antenna_type',
    )

    def antenna_count(self, obj):  # pylint: disable=no-self-use
        """Return the number of antennas"""
        return obj.stations.all().count()

    def station_list(self, obj):  # pylint: disable=no-self-use
        """Return stations that use the antenna"""
        return ",\n".join([str(s.id) for s in obj.stations.all()])


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    """Define Station view in django admin UI"""
    list_display = (
        'id', 'name', 'owner', 'get_email', 'lng', 'lat', 'qthlocator', 'client_version',
        'created_date', 'state', 'target_utilization'
    )
    list_filter = ('status', 'created', 'client_version')
    search_fields = ('id', 'name', 'owner__username')

    actions = [export_as_csv, export_station_status]
    export_as_csv.short_description = "Export selected as CSV"
    export_station_status.short_description = "Export selected status"

    def created_date(self, obj):  # pylint: disable=no-self-use
        """Return when the station was created"""
        return obj.created.strftime('%d.%m.%Y, %H:%M')

    def get_email(self, obj):  # pylint: disable=no-self-use
        """Return station owner email address"""
        return obj.owner.email

    get_email.admin_order_field = 'email'
    get_email.short_description = 'Owner Email'

    def get_actions(self, request):
        """Return the list of actions for station admin view"""
        actions = super(StationAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


@admin.register(Satellite)
class SatelliteAdmin(admin.ModelAdmin):
    """Define Satellite view in django admin UI"""
    list_display = ('id', 'name', 'norad_cat_id', 'manual_tle', 'norad_follow_id', 'status')
    list_filter = (
        'status',
        'manual_tle',
    )
    readonly_fields = ('name', 'names', 'image')
    search_fields = ('name', 'norad_cat_id', 'norad_follow_id')


@admin.register(Tle)
class TleAdmin(admin.ModelAdmin):
    """Define TLE view in django admin UI"""
    list_display = ('satellite_name', 'tle0', 'tle1', 'updated', 'tle_source')
    list_filter = ('tle_source', 'satellite__name')

    def satellite_name(self, obj):  # pylint: disable=no-self-use
        """Return the satellite name"""
        return obj.satellite.name


@admin.register(Transmitter)
class TransmitterAdmin(admin.ModelAdmin):
    """Define Transmitter view in django admin UI"""
    list_display = ('uuid', 'sync_to_db')
    search_fields = ('uuid', )
    list_filter = ('sync_to_db', )
    readonly_fields = ('uuid', )

    def get_urls(self):
        """Returns django urls for the Transmitter view

        sync_to_db -- url for the sync_to_db function

        :returns: Django urls for the Transmitter admin view
        """
        urls = super(TransmitterAdmin, self).get_urls()
        my_urls = [
            url(r'^sync_to_db/$', self.sync_to_db, name='sync_to_db'),
        ]
        return my_urls + urls

    def sync_to_db(self, request):  # pylint: disable=R0201
        """Returns the admin home page, while triggering a Celery sync to DB task

        Forces sync of unsynced demoddata for all transmitters that have set to be synced

        :returns: admin home page redirect with popup message
        """
        sync_to_db.delay()
        messages.success(request, 'Sync to DB task was triggered successfully!')
        return redirect(reverse('admin:index'))


class DemodDataInline(admin.TabularInline):
    """Define DemodData inline template for use in Observation view in django admin UI"""
    model = DemodData


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    """Define Observation view in django admin UI"""
    list_display = ('id', 'author', 'satellite', 'transmitter_uuid', 'start', 'end')
    list_filter = ('start', 'end')
    search_fields = ('satellite', 'author')
    inlines = [
        DemodDataInline,
    ]
    readonly_fields = ('tle', )
