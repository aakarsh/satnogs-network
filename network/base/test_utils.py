"""Tests for miscellaneous functions for SatNOGS Network"""
# pylint: disable=W0621
import pytest

from network.base.utils import community_get_discussion_details


@pytest.fixture
def observation_with_discussion():
    '''Parameters describing an observation for which a discussion exists in the forum'''
    return {
        'observation_id': 1445404,
        'satellite_name': 'OSCAR 7',
        'norad_cat_id': 7530,
        'observation_url': 'https://network.satnogs.org/observations/1445404/'
    }


@pytest.fixture
def observation_without_discussion():
    '''Parameters describing an observation for which no discussion exists in the forum'''
    return {
        'observation_id': 1445405,
        'satellite_name': 'CAS-4B',
        'norad_cat_id': 42759,
        'observation_url': 'https://network.satnogs.org/observations/1445405/'
    }


def test_community_get_discussion_details_with_discussion(observation_with_discussion):
    '''
    Test community_get_discussion_details returns details.has_comments=True and the proper urls
    for the existing discussion in community (details.slug)
    '''
    details = community_get_discussion_details(**observation_with_discussion)

    assert details == {
        'url': 'https://community.libre.space/new-topic?title=Observation 1445404: OSCAR 7 (7530)&'
        'body=Regarding [Observation 1445404](https://network.satnogs.org/observations/1445404/)'
        '...&category=observations',
        'slug': 'https://community.libre.space/t/observation-1445404-oscar-7-7530',
        'has_comments': True
    }


def test_community_get_discussion_details_without_discussion(observation_without_discussion):
    '''
    Test community_get_discussion_details returns details.has_comments=False and the proper urls
    for creating a new discussion in community (details.url)
    '''
    details = community_get_discussion_details(**observation_without_discussion)

    assert details == {
        'url': 'https://community.libre.space/new-topic?title=Observation 1445405: CAS-4B (42759)&'
        'body=Regarding [Observation 1445405](https://network.satnogs.org/observations/1445405/)'
        '...&category=observations',
        'slug': 'https://community.libre.space/t/observation-1445405-cas-4b-42759',
        'has_comments': False
    }
