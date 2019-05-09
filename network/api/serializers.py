from rest_framework import serializers

from network.base.models import Observation, Station, DemodData, Antenna, Transmitter
from network.base.stats import transmitter_stats_by_uuid


class DemodDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemodData
        fields = ('payload_demod', )


class ObservationSerializer(serializers.ModelSerializer):
    transmitter = serializers.SerializerMethodField()
    transmitter_updated = serializers.SerializerMethodField()
    norad_cat_id = serializers.SerializerMethodField()
    station_name = serializers.SerializerMethodField()
    station_lat = serializers.SerializerMethodField()
    station_lng = serializers.SerializerMethodField()
    station_alt = serializers.SerializerMethodField()
    demoddata = DemodDataSerializer(many=True)

    class Meta:
        model = Observation
        fields = ('id', 'start', 'end', 'ground_station', 'transmitter', 'norad_cat_id',
                  'payload', 'waterfall', 'demoddata', 'station_name', 'station_lat',
                  'station_lng', 'station_alt', 'vetted_status', 'archived', 'archive_url',
                  'client_version', 'client_metadata', 'vetted_user', 'vetted_datetime',
                  'rise_azimuth', 'set_azimuth', 'max_altitude', 'transmitter_uuid',
                  'transmitter_description', 'transmitter_type', 'transmitter_uplink_low',
                  'transmitter_uplink_high', 'transmitter_uplink_drift',
                  'transmitter_downlink_low', 'transmitter_downlink_high',
                  'transmitter_downlink_drift', 'transmitter_mode', 'transmitter_invert',
                  'transmitter_baud', 'transmitter_updated', 'tle')
        read_only_fields = ['id', 'start', 'end', 'observation', 'ground_station',
                            'transmitter', 'norad_cat_id', 'archived', 'archive_url',
                            'station_name', 'station_lat', 'station_lng', 'vetted_user',
                            'station_alt', 'vetted_status', 'vetted_datetime', 'rise_azimuth',
                            'set_azimuth', 'max_altitude', 'transmitter_uuid',
                            'transmitter_description', 'transmitter_type',
                            'transmitter_uplink_low', 'transmitter_uplink_high',
                            'transmitter_uplink_drift', 'transmitter_downlink_low',
                            'transmitter_downlink_high', 'transmitter_downlink_drift',
                            'transmitter_mode', 'transmitter_invert', 'transmitter_baud',
                            'transmitter_created', 'transmitter_updated', 'tle']

    def update(self, instance, validated_data):
        validated_data.pop('demoddata')
        super(ObservationSerializer, self).update(instance, validated_data)
        return instance

    def get_transmitter(self, obj):
        try:
            return obj.transmitter_uuid
        except AttributeError:
            return ''

    def get_transmitter_updated(self, obj):
        try:
            return obj.transmitter_created
        except AttributeError:
            return ''

    def get_norad_cat_id(self, obj):
        return obj.satellite.norad_cat_id

    def get_station_name(self, obj):
        try:
            return obj.ground_station.name
        except AttributeError:
            return None

    def get_station_lat(self, obj):
        try:
            return obj.ground_station.lat
        except AttributeError:
            return None

    def get_station_lng(self, obj):
        try:
            return obj.ground_station.lng
        except AttributeError:
            return None

    def get_station_alt(self, obj):
        try:
            return obj.ground_station.alt
        except AttributeError:
            return None


class AntennaSerializer(serializers.ModelSerializer):

    class Meta:
        model = Antenna
        fields = ('frequency', 'frequency_max', 'band', 'antenna_type')


class StationSerializer(serializers.ModelSerializer):
    antenna = AntennaSerializer(many=True)
    altitude = serializers.SerializerMethodField()
    min_horizon = serializers.SerializerMethodField()
    observations = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Station
        fields = ('id', 'name', 'altitude', 'min_horizon', 'lat', 'lng',
                  'qthlocator', 'location', 'antenna', 'created', 'last_seen',
                  'status', 'observations', 'description', 'client_version',
                  'target_utilization')

    def get_altitude(self, obj):
        return obj.alt

    def get_min_horizon(self, obj):
        return obj.horizon

    def get_antenna(self, obj):
        def antenna_name(antenna):
            return (antenna.band + " " + antenna.get_antenna_type_display())
        try:
            return [antenna_name(ant) for ant in obj.antenna.all()]
        except AttributeError:
            return None

    def get_observations(self, obj):
        try:
            return obj.observations_count
        except AttributeError:
            return None

    def get_status(self, obj):
        try:
            return obj.get_status_display()
        except AttributeError:
            return None


class JobSerializer(serializers.ModelSerializer):
    frequency = serializers.SerializerMethodField()
    tle0 = serializers.SerializerMethodField()
    tle1 = serializers.SerializerMethodField()
    tle2 = serializers.SerializerMethodField()
    mode = serializers.SerializerMethodField()
    transmitter = serializers.SerializerMethodField()
    baud = serializers.SerializerMethodField()

    class Meta:
        model = Observation
        fields = ('id', 'start', 'end', 'ground_station', 'tle0', 'tle1', 'tle2',
                  'frequency', 'mode', 'transmitter', 'baud')

    def get_frequency(self, obj):
        frequency = obj.transmitter_downlink_low
        frequency_drift = obj.transmitter_downlink_drift
        if frequency_drift is None:
            return frequency
        else:
            return int(round(frequency + ((frequency * frequency_drift) / float(pow(10, 9)))))

    def get_transmitter(self, obj):
        return obj.transmitter_uuid

    def get_tle0(self, obj):
        return obj.tle.tle0

    def get_tle1(self, obj):
        return obj.tle.tle1

    def get_tle2(self, obj):
        return obj.tle.tle2

    def get_mode(self, obj):
        try:
            return obj.transmitter_mode
        except AttributeError:
            return ''

    def get_baud(self, obj):
        return obj.transmitter_baud


class TransmitterSerializer(serializers.ModelSerializer):
    stats = serializers.SerializerMethodField()

    class Meta:
        model = Transmitter
        fields = ('uuid', 'sync_to_db', 'stats')

    def get_stats(self, obj):
        return transmitter_stats_by_uuid(obj.uuid)
