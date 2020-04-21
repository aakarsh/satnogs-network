"""SatNOGS Network base serializers"""
from rest_framework import serializers

from network.base.models import Station


class StationSerializer(serializers.ModelSerializer):
    """Django model Serializer for Station model"""
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = Station
        fields = ('name', 'lat', 'lng', 'id', 'status', 'status_display')

    def get_status_display(self, obj):  # pylint: disable=no-self-use
        """Returns the station status"""
        try:
            return obj.get_status_display()
        except AttributeError:
            return None
