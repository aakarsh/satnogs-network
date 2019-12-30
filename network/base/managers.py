"""Django base manager for SatNOGS Network"""
from __future__ import absolute_import

from django.db import models
from django.utils.timezone import now


class ObservationManager(models.QuerySet):
    """Observation Manager with extra functionality"""
    def is_future(self):
        """Return future observations"""
        return self.filter(end__gte=now())
