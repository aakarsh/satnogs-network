from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxLengthValidator
from django.db import models
from django.db.models.signals import post_save
from rest_framework.authtoken.models import Token


def gen_token(sender, instance, created, **kwargs):  # pylint: disable=W0613
    try:
        Token.objects.get(user=instance)
    except Token.DoesNotExist:
        Token.objects.create(user=instance)


class User(AbstractUser):
    """Model for SatNOGS users."""

    bio = models.TextField(default='', validators=[MaxLengthValidator(1000)])

    @property
    def displayname(self):
        if self.get_full_name():
            return self.get_full_name()
        return self.username

    def __unicode__(self):
        return self.username


post_save.connect(gen_token, sender=User)
