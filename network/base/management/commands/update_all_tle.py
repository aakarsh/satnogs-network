"""SatNOGS Network django management command to update TLE entries"""
from __future__ import absolute_import

from django.core.management.base import BaseCommand

from network.base.tasks import update_all_tle


class Command(BaseCommand):
    """Django management command to update TLE entries"""
    help = 'Update TLEs for existing Satellites'

    def handle(self, *args, **options):
        update_all_tle()
