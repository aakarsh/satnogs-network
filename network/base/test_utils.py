"""Tests for miscellaneous functions for SatNOGS Network"""
from __future__ import absolute_import

import pytest
from network.base.utils import community_get_discussion_details


@pytest.fixture
def observation_with_discussion():
    """Return an observation with discussion"""
    return {
        'observation_id': 1445404,
        'satellite_name': 'OSCAR 7',
        'norad_cat_id': 7530,
        'observation_url': 'https://network.satnogs.org/observations/1445404/'
    }


@pytest.fixture
def observation_without_discussion():
    """Return an observation without discussion"""
    return {
        'observation_id': 1445405,
        'satellite_name': 'CAS-4B',
        'norad_cat_id': 42759,
        'observation_url': 'https://network.satnogs.org/observations/1445405/'
    }


def test_community_get_discussion_details_with_discussion():
    """Test getting community discussion when it exists"""
    parameters = observation_with_discussion()
    details = community_get_discussion_details(**parameters)

    assert details == {
        'url':
        'https://community.libre.space/new-topic?title=Observation 1445404: OSCAR 7 (7530)&'
        'body=Regarding [Observation 1445404](https://network.satnogs.org/observations/1445404/)'
        '...&category=observations',
        'slug':
        'https://community.libre.space/t/observation-1445404-oscar-7-7530',
        'has_comments':
        True
    }


def test_community_get_discussion_details_without_discussion():
    """Test getting community discussion when it doesn't exists"""
    parameters = observation_without_discussion()
    details = community_get_discussion_details(**parameters)

    assert details == {
        'url':
        'https://community.libre.space/new-topic?title=Observation 1445405: CAS-4B (42759)&'
        'body=Regarding [Observation 1445405](https://network.satnogs.org/observations/1445405/)'
        '...&category=observations',
        'slug':
        'https://community.libre.space/t/observation-1445405-cas-4b-42759',
        'has_comments':
        False
    }
