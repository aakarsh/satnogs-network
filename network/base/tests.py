"""SatNOGS Network base test suites"""
# pylint: disable=R0903
import random
from datetime import datetime, timedelta

import factory
import pytest
from django.contrib.auth.models import Group
from django.db import transaction
from django.test import Client, TestCase
from django.utils.timezone import now
# C0412 below clashes with isort
from factory import fuzzy  # pylint: disable=C0412

from network.base.models import OBSERVATION_STATUSES, Antenna, AntennaType, DemodData, \
    FrequencyRange, Observation, Satellite, Station
from network.base.test_orbital import generate_fake_tle
from network.users.models import User
from network.users.tests import UserFactory

OBSERVATION_STATUS_IDS = [c[0] for c in OBSERVATION_STATUSES]


def generate_payload():
    """Create data payloads"""
    payload = '{0:b}'.format(random.randint(500000000, 510000000))
    digits = 1824
    while digits:
        digit = random.randint(0, 1)
        payload += str(digit)
        digits -= 1
    return payload


def generate_payload_name():
    """Create payload names"""
    filename = datetime.strftime(
        fuzzy.FuzzyDateTime(now() - timedelta(days=10), now()).fuzz(), '%Y%m%dT%H%M%SZ'
    )
    return filename


class StationFactory(factory.django.DjangoModelFactory):
    """Station model factory."""
    owner = factory.SubFactory(UserFactory)
    name = fuzzy.FuzzyText()
    image = factory.django.ImageField()
    alt = fuzzy.FuzzyInteger(0, 800)
    lat = fuzzy.FuzzyFloat(-20, 70)
    lng = fuzzy.FuzzyFloat(-180, 180)
    featured_date = fuzzy.FuzzyDateTime(now() - timedelta(days=10), now())
    testing = fuzzy.FuzzyChoice(choices=[True, False])
    last_seen = fuzzy.FuzzyDateTime(now() - timedelta(days=3), now())
    horizon = fuzzy.FuzzyInteger(10, 20)

    class Meta:
        model = Station


class AntennaFactory(factory.django.DjangoModelFactory):
    """Antenna model factory."""
    antenna_type = factory.Iterator(AntennaType.objects.all())
    station = factory.Iterator(Station.objects.all())

    class Meta:
        model = Antenna


class FrequencyRangeFactory(factory.django.DjangoModelFactory):
    """FrequencyRange model factory."""
    min_frequency = fuzzy.FuzzyInteger(200000000, 500000000)
    max_frequency = fuzzy.FuzzyInteger(500000000, 800000000)
    antenna = factory.Iterator(Antenna.objects.all())

    class Meta:
        model = FrequencyRange


class SatelliteFactory(factory.django.DjangoModelFactory):
    """Satellite model factory."""
    norad_cat_id = fuzzy.FuzzyInteger(2000, 4000)
    name = fuzzy.FuzzyText()

    class Meta:
        model = Satellite


class ObservationFactory(factory.django.DjangoModelFactory):  # pylint: disable=R0902
    """Observation model factory."""
    satellite = factory.SubFactory(SatelliteFactory)
    author = factory.SubFactory(UserFactory)
    start = fuzzy.FuzzyDateTime(
        now() - timedelta(days=3), now() + timedelta(days=3), force_microsecond=0
    )
    end = factory.LazyAttribute(lambda x: x.start + timedelta(minutes=random.randint(5, 12)))
    ground_station = factory.SubFactory(StationFactory)
    tle_line_0 = ''
    tle_line_1 = ''
    tle_line_2 = ''
    tle_source = ''
    tle_updated = None
    payload = factory.django.FileField(filename='data.ogg')
    waterfall_status_datetime = factory.LazyAttribute(
        lambda x: x.end + timedelta(hours=random.randint(1, 20))
    )
    waterfall_status_user = factory.SubFactory(UserFactory)
    waterfall_status = fuzzy.FuzzyChoice(choices=[None, True, False])
    status = fuzzy.FuzzyInteger(-1000, 1000, step=10)
    vetted_status = fuzzy.FuzzyChoice(choices=OBSERVATION_STATUS_IDS)
    transmitter_uuid = fuzzy.FuzzyText(length=20)
    transmitter_description = fuzzy.FuzzyText()
    transmitter_uplink_low = fuzzy.FuzzyInteger(200000000, 500000000, step=10000)
    transmitter_uplink_high = fuzzy.FuzzyInteger(200000000, 500000000, step=10000)
    transmitter_downlink_low = fuzzy.FuzzyInteger(200000000, 500000000, step=10000)
    transmitter_downlink_high = fuzzy.FuzzyInteger(200000000, 500000000, step=10000)
    transmitter_mode = fuzzy.FuzzyText(length=10)
    transmitter_invert = fuzzy.FuzzyChoice(choices=[True, False])
    transmitter_baud = fuzzy.FuzzyInteger(4000, 22000, step=1000)
    transmitter_created = fuzzy.FuzzyDateTime(
        now() - timedelta(days=100),
        now() - timedelta(days=3)
    )

    @factory.post_generation
    def generate_tle(obj, create, extracted, **kwargs):  # pylint: disable=W0613
        "Generate TLE set based on station location and start time of observation"
        date = obj.start + (obj.end - obj.start) / 2
        tle = generate_fake_tle(
            obj.ground_station.lat, obj.ground_station.lng, obj.ground_station.alt, date
        )
        obj.tle_line_0 = tle[0].strip()
        obj.tle_line_1 = tle[1]
        obj.tle_line_2 = tle[2]
        obj.tle_source = 'fake tle'
        obj.tle_updated = obj.start - timedelta(hours=5)

    class Meta:
        model = Observation


class RealisticObservationFactory(ObservationFactory):
    """Observation model factory which uses existing satellites and tles."""
    satellite = factory.Iterator(Satellite.objects.all())
    author = factory.Iterator(User.objects.all())
    ground_station = factory.Iterator(Station.objects.all())
    waterfall_status_user = factory.Iterator(User.objects.all())


class DemodDataFactory(factory.django.DjangoModelFactory):
    """DemodData model factory."""
    observation = factory.Iterator(Observation.objects.all())
    payload_demod = factory.django.FileField()

    class Meta:
        model = DemodData


@pytest.mark.django_db(transaction=True)
class HomeViewTest(TestCase):
    """
    Simple test to make sure the home page is working
    """
    def test_home_page(self):
        """Test for string in home page"""
        response = self.client.get('/')
        self.assertContains(response, 'Crowd-sourced satellite operations')


@pytest.mark.django_db(transaction=True)
class AboutViewTest(TestCase):
    """
    Simple test to make sure the about page is working
    """
    def test_about_page(self):
        """Test for string in about page"""
        response = self.client.get('/about/')
        self.assertContains(response, 'SatNOGS Network is a global management interface')


@pytest.mark.django_db
class StationListViewTest(TestCase):
    """
    Test to ensure the station list is generated by Django
    """
    client = Client()
    stations = []

    def setUp(self):
        for _ in range(1, 10):
            self.stations.append(StationFactory())

    def test_station_list(self):
        """Test for owners and station names in station page"""
        response = self.client.get('/stations/')
        for station in self.stations:
            self.assertContains(response, station.owner)
            self.assertContains(response, station.name)


@pytest.mark.django_db(transaction=True)
class ObservationsListViewTest(TestCase):
    """
    Test to ensure the observation list is generated by Django
    """
    client = Client()
    observations = []
    satellites = []
    stations = []

    def setUp(self):
        # Clear the data and create some new random data
        with transaction.atomic():
            Observation.objects.all().delete()
            Satellite.objects.all().delete()
        self.satellites = []
        self.observations_bad = []
        self.observations_good = []
        self.observations_unknown = []
        self.observations = []
        with transaction.atomic():
            for _ in range(1, 10):
                self.satellites.append(SatelliteFactory())
            for _ in range(1, 10):
                self.stations.append(StationFactory())
            for i in range(1, 5):
                obs = ObservationFactory(status=-100, start=now() - timedelta(days=i))
                self.observations_bad.append(obs)
                self.observations.append(obs)
            for i in range(1, 5):
                obs = ObservationFactory(status=100, start=now() - timedelta(days=i))
                self.observations_good.append(obs)
                self.observations.append(obs)
            for _ in range(1, 5):
                obs = ObservationFactory(status=0)
                self.observations_unknown.append(obs)
                self.observations.append(obs)

    def test_observations_list(self):
        """Test for transmitter modes of each observation in observations page"""
        response = self.client.get('/observations/')
        for observation in self.observations:
            self.assertContains(response, observation.transmitter_mode)

    def test_observations_list_select_bad(self):
        """Test for transmitter modes of each bad observation in observations page"""
        response = self.client.get('/observations/?future=0&good=0&unknown=0&failed=0')

        for observation in self.observations_bad:
            self.assertContains(response, observation.transmitter_mode)

    def test_observations_list_select_good(self):
        """Test for transmitter modes of each good observation in observations page"""
        response = self.client.get('/observations/?future=0&bad=0&unknown=0&failed=0')

        for observation in self.observations_good:
            self.assertContains(response, observation.transmitter_mode)

    def test_observations_list_select_unknown(self):
        """Test for transmitter modes of each unknown observation in observations page"""
        response = self.client.get('/observations/?bad=0&good=0&failed=0')

        for observation in self.observations_unknown:
            self.assertContains(response, observation.transmitter_mode)


class NotFoundErrorTest(TestCase):
    """
    Test the 404 not found handler
    """
    client = Client()

    def test_404_not_found(self):
        """Test for "404" html status code in response for requesting a non-existed page"""
        response = self.client.get('/blah')
        self.assertEqual(response.status_code, 404)


class RobotsViewTest(TestCase):
    """
    Test the robots.txt handler
    """
    client = Client()

    def test_robots(self):
        """Test for "Disallow" string in response for requesting robots.txt"""
        response = self.client.get('/robots.txt')
        self.assertContains(response, 'Disallow: /')


@pytest.mark.django_db(transaction=True)
class ObservationViewTest(TestCase):
    """
    Test to ensure the observation list is generated by Django
    """
    client = Client()
    observation = None
    satellites = []
    stations = []
    user = None

    def setUp(self):
        self.user = UserFactory()
        moderators = Group.objects.get(name='Moderators')
        moderators.user_set.add(self.user)
        for _ in range(1, 10):
            self.satellites.append(SatelliteFactory())
        for _ in range(1, 10):
            self.stations.append(StationFactory())
        self.observation = ObservationFactory()

    def test_observation(self):
        """Test for observer and transmitter mode in observation page"""
        response = self.client.get('/observations/%d/' % self.observation.id)
        self.assertContains(response, self.observation.author.username)
        self.assertContains(response, self.observation.transmitter_mode)


@pytest.mark.django_db(transaction=True)
class ObservationDeleteTest(TestCase):
    """
    Test to ensure the observation list is generated by Django
    """
    client = Client()
    user = None
    future_observation = None
    past_observation = None
    satellites = []

    def setUp(self):
        self.user = UserFactory()
        self.client.force_login(self.user)
        for _ in range(1, 10):
            self.satellites.append(SatelliteFactory())
        self.future_observation = ObservationFactory()
        self.future_observation.author = self.user
        self.future_observation.start = now() + timedelta(days=1)
        self.future_observation.end = self.future_observation.start + timedelta(minutes=15)
        self.future_observation.save()
        self.past_observation = ObservationFactory()
        self.past_observation.author = self.user
        self.past_observation.start = now() - timedelta(days=1)
        self.past_observation.end = self.past_observation.start + timedelta(minutes=15)
        self.past_observation.save()

    def test_future_observation_delete_author(self):
        """Deletion OK when user is the author of the observation and observation is in future"""
        response = self.client.get('/observations/%d/delete/' % self.future_observation.id)
        self.assertRedirects(response, '/observations/')
        response = self.client.get('/observations/')
        with self.assertRaises(Observation.DoesNotExist):
            _lookup = Observation.objects.get(pk=self.future_observation.id)  # noqa:F841

    def test_future_observation_delete_moderator(self):
        """Deletion OK when user is moderator and observation is in future"""
        self.user = UserFactory()
        moderators = Group.objects.get(name='Moderators')
        moderators.user_set.add(self.user)
        self.client.force_login(self.user)
        response = self.client.get('/observations/%d/delete/' % self.future_observation.id)
        self.assertRedirects(response, '/observations/')
        response = self.client.get('/observations/')
        with self.assertRaises(Observation.DoesNotExist):
            _lookup = Observation.objects.get(pk=self.future_observation.id)  # noqa:F841

    def test_past_observation_delete_author(self):
        """Deletion NOT OK when user is the author of the observation and observation is in past"""
        response = self.client.get('/observations/%d/delete/' % self.past_observation.id)
        self.assertRedirects(response, '/observations/')
        response = self.client.get('/observations/')
        self.assertContains(response, self.past_observation.id)

    def test_past_observation_delete_moderator(self):
        """Deletion NOT OK when user is moderator and observation is in past"""
        self.user = UserFactory()
        moderators = Group.objects.get(name='Moderators')
        moderators.user_set.add(self.user)
        self.client.force_login(self.user)
        response = self.client.get('/observations/%d/delete/' % self.past_observation.id)
        self.assertRedirects(response, '/observations/')
        response = self.client.get('/observations/')
        self.assertContains(response, self.past_observation.id)


@pytest.mark.django_db(transaction=True)
class StationViewTest(TestCase):
    """
    Test to ensure the observation list is generated by Django
    """
    client = Client()
    station = None

    def setUp(self):
        self.station = StationFactory()

    def test_observation(self):
        """Test for owner, elevation and min horizon in station page"""
        response = self.client.get('/stations/%d/' % self.station.id)
        self.assertContains(response, self.station.owner.username)
        self.assertContains(response, self.station.alt)
        self.assertContains(response, self.station.horizon)


@pytest.mark.django_db(transaction=True)
class StationDeleteTest(TestCase):
    """
    Test to ensure the observation list is generated by Django
    """
    client = Client()
    station = None
    user = None

    def setUp(self):
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.station = StationFactory()
        self.station.owner = self.user
        self.station.save()

    def test_station_delete(self):
        """Test deletion of station"""
        response = self.client.get('/stations/%d/delete/' % self.station.id)
        self.assertRedirects(response, '/users/%s/' % self.user.username)
        with self.assertRaises(Station.DoesNotExist):
            _lookup = Station.objects.get(pk=self.station.id)  # noqa:F841


@pytest.mark.django_db(transaction=True)
class SettingsSiteViewTest(TestCase):
    """
    Test to ensure the satellite fetch feature works
    """
    client = Client()
    user = None

    def setUp(self):
        self.user = UserFactory()
        self.user.is_staff = True
        self.user.save()
        self.client.force_login(self.user)

    def test_get(self):
        """Test for "Fetch Data" in Settings Site page"""
        response = self.client.get('/settings_site/')
        self.assertContains(response, 'Fetch Data')


@pytest.mark.django_db(transaction=True)
class ObservationModelTest(TestCase):
    """
    Test various properties of the Observation Model
    """
    observation = None
    satellites = []
    user = None
    admin = None

    def setUp(self):
        for _ in range(1, 10):
            self.satellites.append(SatelliteFactory())
        self.observation = ObservationFactory()
        self.observation.end = now()
        self.observation.save()

    def test_is_passed(self):
        """Test for observation be in past"""
        self.assertTrue(self.observation.is_past)
