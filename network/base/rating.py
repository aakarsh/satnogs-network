"""Observation rating functions for SatNOGS Network"""


def get_observation_status_rate(observation, action, action_value=None):
    """
    Return observation_status value for given observation and action

    Logic of returned value of action "set_waterfall_status":

                With  Without Unknown
        Failed  100   same    same
        Bad     100   same    0
        Unknown 100   -100    0
        Good    100   -100    0

    """
    if action == "set_waterfall_status":
        if action_value:
            return 100
        if action_value is None and observation.observation_status >= -100:
            return 0
        if not action_value and observation.observation_status >= 0:
            return -100
    return observation.observation_status
