"""SatNOGS Network API test suites"""
from __future__ import absolute_import

import json

import pytest
from django.test import TestCase
from rest_framework.utils.encoders import JSONEncoder

from network.base.tests import AntennaFactory, FrequencyRangeFactory, \
    ObservationFactory, SatelliteFactory, StationFactory


@pytest.mark.django_db(transaction=True)
class JobViewApiTest(TestCase):
    """
    Tests the Job View API
    """
    observation = None
    satellites = []
    stations = []

    def setUp(self):
        for _ in range(1, 10):
            self.satellites.append(SatelliteFactory())
        for _ in range(1, 10):
            self.stations.append(StationFactory())
        self.observation = ObservationFactory()

    def test_job_view_api(self):
        """Test the Job View API"""
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
        self.encoder = JSONEncoder()
        self.station = StationFactory()
        self.antenna = AntennaFactory(station=self.station)
        self.frequency_range = FrequencyRangeFactory(antenna=self.antenna)

    def test_station_view_api(self):
        """Test the Station View API"""

        antenna_types = {
            'Dipole': 'dipole',
            'V-Dipole': 'v-dipole',
            'Discone': 'discone',
            'Ground Plane': 'ground',
            'Yagi': 'yagi',
            'Cross Yagi': 'cross-yagi',
            'Helical': 'helical',
            'Parabolic': 'parabolic',
            'Vertical': 'vertical',
            'Turnstile': 'turnstile',
            'Quadrafilar': 'quadrafilar',
            'Eggbeater': 'eggbeater',
            'Lindenblad': 'lindenblad',
            'Parasitic Lindenblad': 'paralindy',
            'Patch': 'patch',
            'Other Directional': 'other direct',
            'Other Omni-Directional': 'other omni',
        }

        ser_ants = [
            {
                u'band': self.frequency_range.bands,
                u'frequency': self.frequency_range.min_frequency,
                u'frequency_max': self.frequency_range.max_frequency,
                u'antenna_type': antenna_types[self.antenna.antenna_type.name],
                u'antenna_type_name': self.antenna.antenna_type.name,
            }
        ]

        station_serialized = {
            u'id': self.station.id,
            u'altitude': self.station.alt,
            u'antenna': ser_ants,
            u'client_version': self.station.client_version,
            u'created': self.encoder.default(self.station.created),
            u'description': self.station.description,
            u'last_seen': self.encoder.default(self.station.last_seen),
            u'lat': self.station.lat,
            u'lng': self.station.lng,
            u'min_horizon': self.station.horizon,
            u'name': self.station.name,
            u'observations': 0,
            u'qthlocator': self.station.qthlocator,
            u'target_utilization': self.station.target_utilization,
            u'status': self.station.get_status_display(),
        }

        response = self.client.get('/api/stations/')
        response_json = json.loads(response.content)
        self.assertEqual(response_json, [station_serialized])
