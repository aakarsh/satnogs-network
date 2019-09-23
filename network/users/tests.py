import datetime

import factory
from django.test import Client, TestCase
from django.utils.timezone import utc
from factory import fuzzy

import pytest
from network.users.models import User


class UserFactory(factory.django.DjangoModelFactory):
    """User model factory."""
    username = factory.Sequence(lambda n: 'username%s' % n)
    first_name = 'John'
    last_name = factory.Sequence(lambda n: 'Doe %s' % n)
    email = factory.LazyAttribute(lambda o: '%s@example.com' % o.username)
    password = factory.PostGenerationMethodCall('set_password', 'passwd')
    is_staff = False
    is_active = True
    is_superuser = False
    last_login = datetime.datetime(2012, 1, 1, tzinfo=utc)
    date_joined = datetime.datetime(2012, 1, 1, tzinfo=utc)
    bio = fuzzy.FuzzyText()

    class Meta:
        model = User


@pytest.mark.django_db
class UserViewTest(TestCase):
    """
    Tests the user detail view
    """
    client = Client()
    user = None

    def setUp(self):
        self.user = UserFactory()
        self.client.force_login(self.user)

    def test_view_user(self):
        response = self.client.get('/users/%s/' % self.user.username)
        self.assertContains(response, self.user.username)
