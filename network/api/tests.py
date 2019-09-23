import json

from django.test import TestCase
from rest_framework.utils.encoders import JSONEncoder

import pytest
from network.base.tests import AntennaFactory, ObservationFactory, \
    SatelliteFactory, StationFactory


@pytest.mark.django_db(transaction=True)
class JobViewApiTest(TestCase):
    """
    Tests the Job View API
    """
    observation = None
    satellites = []
    stations = []

    def setUp(self):
        for x in xrange(1, 10):
            self.satellites.append(SatelliteFactory())
        for x in xrange(1, 10):
            self.stations.append(StationFactory())
        self.observation = ObservationFactory()

    def test_job_view_api(self):
        response = self.client.get('/api/jobs/')
        response_json = json.loads(response.content)
        self.assertEqual(response_json, [])


@pytest.mark.django_db(transaction=True)
class StationViewApiTest(TestCase):
    """
    Tests the Station View API
    """
    station = None

    def setUp(self):
        self.antenna = AntennaFactory()
        self.encoder = JSONEncoder()
        self.station = StationFactory.create(antennas=[self.antenna])

    def test_station_view_api(self):

        ants = self.station.antenna.all()
        ser_ants = [{u'band': ant.band,
                     u'frequency': ant.frequency,
                     u'frequency_max': ant.frequency_max,
                     u'antenna_type': ant.antenna_type} for ant in ants]

        station_serialized = {
            u'altitude': self.station.alt,
            u'antenna': ser_ants,
            u'client_version': self.station.client_version,
            u'created': self.encoder.default(self.station.created),
            u'description': self.station.description,
            u'id': self.station.id,
            u'last_seen': self.encoder.default(self.station.last_seen),
            u'lat': self.station.lat,
            u'lng': self.station.lng,
            u'location': self.station.location,
            u'min_horizon': self.station.horizon,
            u'name': self.station.name,
            u'observations': 0,
            u'qthlocator': self.station.qthlocator,
            u'target_utilization': self.station.target_utilization,
            u'status': self.station.get_status_display()}

        response = self.client.get('/api/stations/')
        response_json = json.loads(response.content)
        self.assertEqual(response_json, [station_serialized])
