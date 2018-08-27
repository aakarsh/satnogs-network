from django.contrib import admin

from network.base.models import (Antenna, Satellite, Station, Transmitter,
                                 Observation, Mode, Tle, Rig, DemodData)


@admin.register(Rig)
class RigAdmin(admin.ModelAdmin):
    list_display = ('name', 'rictld_number')
    list_filter = ('name', )


@admin.register(Mode)
class ModeAdmin(admin.ModelAdmin):
    list_display = ('name', )
    readonly_fields = ('name', )


@admin.register(Antenna)
class AntennaAdmin(admin.ModelAdmin):
    list_display = ('id', '__unicode__', 'antenna_count', 'station_list', )
    list_filter = ('band', 'antenna_type', )

    def antenna_count(self, obj):
        return obj.stations.all().count()

    def station_list(self, obj):
        return ",\n".join([str(s.id) for s in obj.stations.all()])


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'owner', 'lng', 'lat', 'qthlocator', 'client_version',
                    'created_date', 'state')
    list_filter = ('status', 'created', 'client_version')

    def created_date(self, obj):
        return obj.created.strftime('%d.%m.%Y, %H:%M')


@admin.register(Satellite)
class SatelliteAdmin(admin.ModelAdmin):
    list_display = ('name', 'norad_cat_id')
    readonly_fields = ('name', 'names', 'image')


@admin.register(Tle)
class TleAdmin(admin.ModelAdmin):
    list_display = ('tle0', 'tle1', 'updated_date')
    list_filter = ('tle0', )

    def updated_date(self, obj):
        return obj.updated.strftime('%d.%m.%Y, %H:%M')


@admin.register(Transmitter)
class TransmitterAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'description', 'satellite', 'uplink_low',
                    'uplink_high', 'downlink_low', 'downlink_high')
    search_fields = ('satellite', 'uuid')
    list_filter = ('mode', 'invert')
    readonly_fields = ('uuid', 'description', 'satellite', 'uplink_low', 'uplink_high',
                       'downlink_low', 'downlink_high', 'baud', 'invert', 'alive', 'mode')


class DataDemodInline(admin.TabularInline):
    model = DemodData


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'satellite', 'transmitter', 'start_date', 'end_date')
    list_filter = ('start', 'end')
    search_fields = ('satellite', 'author')
    inlines = [
        DataDemodInline,
    ]

    def start_date(self, obj):
        return obj.start.strftime('%d.%m.%Y, %H:%M')

    def end_date(self, obj):
        return obj.end.strftime('%d.%m.%Y, %H:%M')
