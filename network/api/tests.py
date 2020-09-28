"""SatNOGS Network API test suites"""
import json

import pytest
from django.test import TestCase
from rest_framework.utils.encoders import JSONEncoder

from network.base.tests import AntennaFactory, FrequencyRangeFactory, ObservationFactory, \
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
                'band': self.frequency_range.bands,
                'frequency': self.frequency_range.min_frequency,
                'frequency_max': self.frequency_range.max_frequency,
                'antenna_type': antenna_types[self.antenna.antenna_type.name],
                'antenna_type_name': self.antenna.antenna_type.name,
            }
        ]

        station_serialized = {
            'id': self.station.id,
            'altitude': self.station.alt,
            'antenna': ser_ants,
            'client_version': self.station.client_version,
            'created': self.encoder.default(self.station.created),
            'description': self.station.description,
            'last_seen': self.encoder.default(self.station.last_seen),
            'lat': self.station.lat,
            'lng': self.station.lng,
            'min_horizon': self.station.horizon,
            'name': self.station.name,
            'observations': 0,
            'qthlocator': self.station.qthlocator,
            'target_utilization': self.station.target_utilization,
            'status': self.station.get_status_display(),
        }

        response = self.client.get('/api/stations/')
        response_json = json.loads(response.content)
        self.assertEqual(response_json, [station_serialized])
