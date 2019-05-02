def downlink_low_is_in_range(antenna, transmitter):
    if transmitter['downlink_low'] is not None:
        return antenna.frequency <= transmitter['downlink_low'] <= antenna.frequency_max
    else:
        return False
