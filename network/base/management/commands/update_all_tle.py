from django.core.management.base import BaseCommand

from network.base.tasks import update_all_tle


class Command(BaseCommand):
    help = 'Update TLEs for existing Satellites'

    def handle(self, *args, **options):
        update_all_tle()
