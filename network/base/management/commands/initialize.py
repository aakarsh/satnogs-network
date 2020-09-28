"""SatNOGS Network django management command to initialize a new database"""
from django.core.management import call_command
from django.core.management.base import BaseCommand

from network.base.models import AntennaType
from network.base.tests import AntennaFactory, DemodDataFactory, FrequencyRangeFactory, \
    RealisticObservationFactory, StationFactory, generate_payload, generate_payload_name


class Command(BaseCommand):
    """Django management command to initialize a new database"""
    help = 'Create initial fixtures'

    def handle(self, *args, **options):
        station_fixture_count = 40
        antenna_fixture_count = 50
        observation_fixture_count = 200
        demoddata_fixture_count = 40

        # Migrate
        self.stdout.write("Creating database...")
        call_command('migrate')

        #  Initial data
        call_command('fetch_data')

        # Check if migration AntennaType data have been removed
        if not AntennaType.objects.all():
            AntennaType.objects.bulk_create(
                [
                    AntennaType(name="Dipole"),
                    AntennaType(name="V-Dipole"),
                    AntennaType(name="Discone"),
                    AntennaType(name="Ground Plane"),
                    AntennaType(name="Yagi"),
                    AntennaType(name="Cross Yagi"),
                    AntennaType(name="Helical"),
                    AntennaType(name="Parabolic"),
                    AntennaType(name="Vertical"),
                    AntennaType(name="Turnstile"),
                    AntennaType(name="Quadrafilar"),
                    AntennaType(name="Eggbeater"),
                    AntennaType(name="Lindenblad"),
                    AntennaType(name="Parasitic Lindenblad"),
                    AntennaType(name="Patch"),
                    AntennaType(name="Other Directional"),
                    AntennaType(name="Other Omni-Directional"),
                ]
            )

        # Create random fixtures for remaining models
        self.stdout.write("Creating fixtures...")
        StationFactory.create_batch(station_fixture_count)
        AntennaFactory.create_batch(antenna_fixture_count)
        FrequencyRangeFactory.create_batch(antenna_fixture_count)
        self.stdout.write("Added {} stations.".format(station_fixture_count))
        RealisticObservationFactory.create_batch(observation_fixture_count)
        self.stdout.write("Added {} observations.".format(observation_fixture_count))
        for _ in range(demoddata_fixture_count):
            DemodDataFactory.create(
                payload_demod__data=generate_payload(),
                payload_demod__filename=generate_payload_name()
            )
        self.stdout.write("Added {} DemodData objects.".format(demoddata_fixture_count))

        # Create superuser
        self.stdout.write("Creating a superuser...")
        call_command('createsuperuser')
