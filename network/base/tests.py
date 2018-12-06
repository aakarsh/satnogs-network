import random
from datetime import datetime, timedelta
import pytest

import factory
from factory import fuzzy

from django.db import transaction
from django.contrib.auth.models import Group
from django.test import TestCase, Client
from django.utils.timezone import now

from network.base.models import (ANTENNA_BANDS, ANTENNA_TYPES, OBSERVATION_STATUSES,
                                 Mode, Antenna, Satellite, Tle, Station, Transmitter,
                                 Observation, DemodData)
from network.users.tests import UserFactory


ANTENNA_BAND_IDS = [c[0] for c in ANTENNA_BANDS]
ANTENNA_TYPE_IDS = [c[0] for c in ANTENNA_TYPES]
OBSERVATION_STATUS_IDS = [c[0] for c in OBSERVATION_STATUSES]


def generate_payload():
    payload = '{0:b}'.format(random.randint(500000000, 510000000))
    digits = 1824
    while digits:
        digit = random.randint(0, 1)
        payload += str(digit)
        digits -= 1
    return payload


def generate_payload_name():
    filename = datetime.strftime(fuzzy.FuzzyDateTime(now() - timedelta(days=10), now()).fuzz(),
                                 '%Y%m%dT%H%M%SZ')
    return filename


def get_valid_satellites():
    qs = Transmitter.objects.all()
    satellites = Satellite.objects.filter(transmitters__in=qs).distinct()
    return satellites


class ModeFactory(factory.django.DjangoModelFactory):
    """Mode model factory."""
    name = fuzzy.FuzzyText()

    class Meta:
        model = Mode


class AntennaFactory(factory.django.DjangoModelFactory):
    """Antenna model factory."""
    frequency = fuzzy.FuzzyFloat(200, 500)
    frequency_max = fuzzy.FuzzyFloat(500, 800)
    band = fuzzy.FuzzyChoice(choices=ANTENNA_BAND_IDS)
    antenna_type = fuzzy.FuzzyChoice(choices=ANTENNA_TYPE_IDS)

    class Meta:
        model = Antenna


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

    @factory.post_generation
    def antennas(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for antenna in extracted:
                if random.randint(0, 1):
                    self.antenna.add(antenna)

    class Meta:
        model = Station


class SatelliteFactory(factory.django.DjangoModelFactory):
    """Sattelite model factory."""
    norad_cat_id = fuzzy.FuzzyInteger(2000, 4000)
    name = fuzzy.FuzzyText()

    class Meta:
        model = Satellite


class TleFactory(factory.django.DjangoModelFactory):
    """Tle model factory."""
    tle0 = 'ISS (ZARYA)'
    tle1 = '1 25544U 98067A   17355.27738426  .00002760  00000-0  48789-4 0  9995'
    tle2 = '2 25544  51.6403 185.6460 0002546 270.9261  71.9125 15.54204066 90844'
    updated = fuzzy.FuzzyDateTime(now() - timedelta(days=3), now())
    satellite = factory.SubFactory(SatelliteFactory)

    class Meta:
        model = Tle


class TransmitterFactory(factory.django.DjangoModelFactory):
    """Transmitter model factory."""
    description = fuzzy.FuzzyText()
    alive = fuzzy.FuzzyChoice(choices=[True, False])
    uplink_low = fuzzy.FuzzyInteger(200000000, 500000000, step=10000)
    uplink_high = fuzzy.FuzzyInteger(200000000, 500000000, step=10000)
    downlink_low = fuzzy.FuzzyInteger(200000000, 500000000, step=10000)
    downlink_high = fuzzy.FuzzyInteger(200000000, 500000000, step=10000)
    mode = factory.SubFactory(ModeFactory)
    invert = fuzzy.FuzzyChoice(choices=[True, False])
    baud = fuzzy.FuzzyInteger(4000, 22000, step=1000)
    satellite = factory.SubFactory(SatelliteFactory)

    class Meta:
        model = Transmitter


class ObservationFactory(factory.django.DjangoModelFactory):
    """Observation model factory."""
    satellite = factory.Iterator(get_valid_satellites())
    tle = factory.SubFactory(TleFactory)
    author = factory.SubFactory(UserFactory)
    start = fuzzy.FuzzyDateTime(now() - timedelta(days=3),
                                now() + timedelta(days=3))
    end = factory.LazyAttribute(
        lambda x: x.start + timedelta(hours=random.randint(1, 8))
    )
    ground_station = factory.Iterator(Station.objects.all())
    payload = factory.django.FileField(filename='data.ogg')
    vetted_datetime = factory.LazyAttribute(
        lambda x: x.end + timedelta(hours=random.randint(1, 20))
    )
    vetted_user = factory.SubFactory(UserFactory)
    vetted_status = fuzzy.FuzzyChoice(choices=OBSERVATION_STATUS_IDS)

    @factory.lazy_attribute
    def transmitter(self):
        return self.satellite.transmitters.all().order_by('?')[0]

    class Meta:
        model = Observation


class DemodDataFactory(factory.django.DjangoModelFactory):
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
        response = self.client.get('/')
        self.assertContains(response, 'Crowd-sourced satellite operations')


@pytest.mark.django_db(transaction=True)
class AboutViewTest(TestCase):
    """
    Simple test to make sure the about page is working
    """
    def test_about_page(self):
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
        for x in xrange(1, 10):
            self.stations.append(StationFactory())

    def test_station_list(self):
        response = self.client.get('/stations/')
        for x in self.stations:
            self.assertContains(response, x.owner)
            self.assertContains(response, x.name)


@pytest.mark.django_db(transaction=True)
class ObservationsListViewTest(TestCase):
    """
    Test to ensure the observation list is generated by Django
    """
    client = Client()
    observations = []
    satellites = []
    transmitters = []
    stations = []

    def setUp(self):
        # Clear the data and create some new random data
        with transaction.atomic():
            Observation.objects.all().delete()
            Transmitter.objects.all().delete()
            Satellite.objects.all().delete()
        self.satellites = []
        self.transmitters = []
        self.observations_bad = []
        self.observations_good = []
        self.observations_unvetted = []
        self.observations = []
        with transaction.atomic():
            for x in xrange(1, 10):
                self.satellites.append(SatelliteFactory())
            for x in xrange(1, 10):
                self.transmitters.append(TransmitterFactory())
            for x in xrange(1, 10):
                self.stations.append(StationFactory())
            for x in xrange(1, 10):
                obs = ObservationFactory(vetted_status='bad')
                self.observations_bad.append(obs)
                self.observations.append(obs)
            for x in xrange(1, 10):
                obs = ObservationFactory(vetted_status='good')
                self.observations_good.append(obs)
                self.observations.append(obs)
            for x in xrange(1, 10):
                obs = ObservationFactory(vetted_status='unknown')
                self.observations_unvetted.append(obs)
                self.observations.append(obs)

    def test_observations_list(self):
        response = self.client.get('/observations/')

        for x in self.observations:
            self.assertContains(response, x.transmitter.mode.name)

    def test_observations_list_select_bad(self):
        response = self.client.get('/observations/?bad=1')

        for x in self.observations_bad:
            self.assertContains(response, x.transmitter.mode.name)

    def test_observations_list_select_good(self):
        response = self.client.get('/observations/?good=1')

        for x in self.observations_good:
            self.assertContains(response, x.transmitter.mode.name)

    def test_observations_list_select_unvetted(self):
        response = self.client.get('/observations/?unvetted=1')

        for x in self.observations_unvetted:
            self.assertContains(response, x.transmitter.mode.name)


class NotFoundErrorTest(TestCase):
    """
    Test the 404 not found handler
    """
    client = Client()

    def test_404_not_found(self):
        response = self.client.get('/blah')
        self.assertEquals(response.status_code, 404)


class RobotsViewTest(TestCase):
    """
    Test the robots.txt handler
    """
    client = Client()

    def test_robots(self):
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
    transmitters = []
    stations = []
    user = None

    def setUp(self):
        self.user = UserFactory()
        g = Group.objects.get(name='Moderators')
        g.user_set.add(self.user)
        for x in xrange(1, 10):
            self.satellites.append(SatelliteFactory())
        for x in xrange(1, 10):
            self.transmitters.append(TransmitterFactory())
        for x in xrange(1, 10):
            self.stations.append(StationFactory())
        self.observation = ObservationFactory()

    def test_observation(self):
        response = self.client.get('/observations/%d/' % self.observation.id)
        self.assertContains(response, self.observation.author.username)
        self.assertContains(response, self.observation.transmitter.mode.name)


@pytest.mark.django_db(transaction=True)
class ObservationDeleteTest(TestCase):
    """
    Test to ensure the observation list is generated by Django
    """
    client = Client()
    user = None
    observation = None
    satellites = []
    transmitters = []

    def setUp(self):
        self.user = UserFactory()
        self.client.force_login(self.user)
        for x in xrange(1, 10):
            self.satellites.append(SatelliteFactory())
        for x in xrange(1, 10):
            self.transmitters.append(TransmitterFactory())
        self.observation = ObservationFactory()
        self.observation.author = self.user
        self.observation.save()

    def test_observation_delete_author(self):
        """Deletion OK when user is the author of the observation"""
        response = self.client.get('/observations/%d/delete/' % self.observation.id)
        self.assertRedirects(response, '/observations/')
        response = self.client.get('/observations/')
        with self.assertRaises(Observation.DoesNotExist):
            _lookup = Observation.objects.get(pk=self.observation.id)  # noqa:F841

    def test_observation_delete_moderator(self):
        """Deletion OK when user is moderator and there is no data"""
        self.user = UserFactory()
        g = Group.objects.get(name='Moderators')
        g.user_set.add(self.user)
        self.client.force_login(self.user)
        response = self.client.get('/observations/%d/delete/' % self.observation.id)
        self.assertRedirects(response, '/observations/')
        response = self.client.get('/observations/')
        with self.assertRaises(Observation.DoesNotExist):
            _lookup = Observation.objects.get(pk=self.observation.id)  # noqa:F841


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
        response = self.client.get('/stations/%d/delete/' % self.station.id)
        self.assertRedirects(response, '/users/%s/' % self.user.username)
        with self.assertRaises(Station.DoesNotExist):
            _lookup = Station.objects.get(pk=self.station.id)       # noqa:F841


@pytest.mark.django_db(transaction=True)
class SettingsSiteViewTest(TestCase):
    """
    Test to ensure the satellite fetch feature works
    """
    client = Client()
    user = None

    def setUp(self):
        self.user = UserFactory()
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)

    def test_get(self):
        response = self.client.get('/settings_site/')
        self.assertContains(response, 'Fetch Data')


@pytest.mark.django_db(transaction=True)
class ObservationVetViewtest(TestCase):
    """
    Test vetting data
    """
    client = Client()
    user = None
    satellites = []
    stations = []
    transmitters = []
    observations = []

    def setUp(self):
        self.user = UserFactory()
        g = Group.objects.get(name='Moderators')
        g.user_set.add(self.user)
        self.client.force_login(self.user)
        for x in xrange(1, 10):
            self.satellites.append(SatelliteFactory())
        for x in xrange(1, 10):
            self.transmitters.append(TransmitterFactory())
        for x in xrange(1, 10):
            self.stations.append(StationFactory())
        for x in xrange(1, 5):
            self.observations.append(ObservationFactory(vetted_status='unknown'))

    def test_get_observation_vet_good(self):
        obs = self.observations[0]
        response = self.client.get('/observation_vet/%d/good/' % obs.id)
        self.assertRedirects(response, '/observations/%d/' % obs.id)
        observation = Observation.objects.get(id=obs.id)
        self.assertEqual(observation.vetted_user.username, self.user.username)
        self.assertEqual(observation.vetted_status, 'good')

    def test_get_observation_vet_bad(self):
        obs = self.observations[1]
        response = self.client.get('/observation_vet/%d/bad/' % obs.id)
        self.assertRedirects(response, '/observations/%d/' % obs.id)
        observation = Observation.objects.get(id=obs.id)
        self.assertEqual(observation.vetted_user.username, self.user.username)
        self.assertEqual(observation.vetted_status, 'bad')

    def test_get_observation_vet_failed(self):
        obs = self.observations[2]
        response = self.client.get('/observation_vet/%d/failed/' % obs.id)
        self.assertRedirects(response, '/observations/%d/' % obs.id)
        observation = Observation.objects.get(id=obs.id)
        self.assertEqual(observation.vetted_user.username, self.user.username)
        self.assertEqual(observation.vetted_status, 'failed')

    def test_get_observation_undo_vet(self):
        obs = self.observations[0]
        response = self.client.get('/observation_vet/%d/unknown/' % obs.id)
        self.assertRedirects(response, '/observations/%d/' % obs.id)
        observation = Observation.objects.get(id=obs.id)
        self.assertEqual(observation.vetted_status, 'unknown')


@pytest.mark.django_db(transaction=True)
class SatelliteModelTest(TestCase):
    """
    Tests various methods of the Satellite model
    """
    satellite = None

    def setUp(self):
        self.satellite = SatelliteFactory()

    def test_latest_tle(self):
        self.assertFalse(self.satellite.latest_tle)

    def test_tle_epoch(self):
        self.assertFalse(self.satellite.tle_epoch)

    def test_tle_no(self):
        self.assertFalse(self.satellite.tle_no)


@pytest.mark.django_db(transaction=True)
class ObservationModelTest(TestCase):
    """
    Test various properties of the Observation Model
    """
    observation = None
    satellites = []
    transmitters = []
    user = None
    admin = None

    def setUp(self):
        for x in xrange(1, 10):
            self.satellites.append(SatelliteFactory())
        for x in xrange(1, 10):
            self.transmitters.append(TransmitterFactory())
        self.observation = ObservationFactory()
        self.observation.end = now()
        self.observation.save()

    def test_is_passed(self):
        self.assertTrue(self.observation.is_past)
