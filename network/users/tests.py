"""SatNOGS Network users test suites"""
import datetime

import factory
import pytest
from django.test import Client, TestCase
from django.utils.timezone import utc
# C0412 below clashes with isort
from factory import fuzzy  # pylint: disable=C0412

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
        """Test of user view"""
        response = self.client.get('/users/%s/' % self.user.username)
        self.assertContains(response, self.user.username)
