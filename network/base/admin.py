from django.contrib import admin

from network.base.models import Antenna, DemodData, Observation, Satellite, \
    Station, Tle, Transmitter
from network.base.utils import export_as_csv, export_station_status


@admin.register(Antenna)
class AntennaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        '__unicode__',
        'antenna_count',
        'station_list',
    )
    list_filter = (
        'band',
        'antenna_type',
    )

    def antenna_count(self, obj):
        return obj.stations.all().count()

    def station_list(self, obj):
        return ",\n".join([str(s.id) for s in obj.stations.all()])


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'owner', 'get_email', 'lng', 'lat', 'qthlocator', 'client_version',
        'created_date', 'state', 'target_utilization'
    )
    list_filter = ('status', 'created', 'client_version')
    search_fields = ('id', 'name', 'owner__username')

    actions = [export_as_csv, export_station_status]
    export_as_csv.short_description = "Export selected as CSV"
    export_station_status.short_description = "Export selected status"

    def created_date(self, obj):
        return obj.created.strftime('%d.%m.%Y, %H:%M')

    def get_email(self, obj):
        return obj.owner.email

    get_email.admin_order_field = 'email'
    get_email.short_description = 'Owner Email'

    def get_actions(self, request):
        actions = super(StationAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


@admin.register(Satellite)
class SatelliteAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'norad_cat_id', 'manual_tle', 'norad_follow_id', 'status')
    list_filter = (
        'status',
        'manual_tle',
    )
    readonly_fields = ('name', 'names', 'image')
    search_fields = ('name', 'norad_cat_id', 'norad_follow_id')


@admin.register(Tle)
class TleAdmin(admin.ModelAdmin):
    list_display = ('satellite_name', 'tle0', 'tle1', 'updated')
    list_filter = ('satellite__name', )

    def satellite_name(self, obj):
        return obj.satellite.name


@admin.register(Transmitter)
class TransmitterAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'sync_to_db')
    search_fields = ('uuid', )
    list_filter = ('sync_to_db', )
    readonly_fields = ('uuid', )


class DemodDataInline(admin.TabularInline):
    """Defines DemodData inline template for use in Observation view in django admin UI"""
    model = DemodData


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'satellite', 'transmitter_uuid', 'start', 'end')
    list_filter = ('start', 'end')
    search_fields = ('satellite', 'author')
    inlines = [
        DemodDataInline,
    ]
    readonly_fields = ('tle', )
