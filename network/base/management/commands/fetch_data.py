"""SatNOGS Network django management command to fetch data (Satellites and Transmitters)"""
from django.core.management.base import BaseCommand, CommandError
# Remove this import after Python 3 migration
from requests.exceptions import ConnectionError  # pylint: disable=W0622

from network.base.tasks import fetch_data


class Command(BaseCommand):
    """Django management command to fetch Satellites and Transmitters from SatNOGS DB"""
    help = 'Fetches Satellites and Transmitters from SaTNOGS DB'

    def handle(self, *args, **options):
        try:
            fetch_data()
        except ConnectionError as exception:
            raise CommandError(exception) from exception
