""" Testing some functionality for the Prologix Resource manager. """

import pytest
from lightlab.equipment.visa_bases.prologix_gpib import \
    _validate_hostname, \
    _sanitize_address, \
    PrologixGPIBObject


def test_valid_hostnames():
    trials = [('princeton.edu', True),
              ('princeton.edu.123', False),
              ('a.b.c', True),
              ('a.b', True),
              ('abc', True),
              ('12.132.132.1', True),
              ('0.0.0.0', True),
              ('0.0.0.0.0', False),
              ('127.0.0.1', True),
              ('300.0.0.1', False),
              ]
    for trial_name, trial_result in trials:
        assert _validate_hostname(trial_name) is trial_result


addresses = [("prologix://princeton.edu/1:0", "princeton.edu", 1, 0),
             ("prologix://princeton.edu/1", "princeton.edu", 1, None),
             ("prologix://princeton.edu/-1:123", "princeton.edu", -1, 123),
             ]


@pytest.mark.parametrize("address", addresses)
def test_sanitize_address(address):
    address, true_ip_address, true_gpib_pad, true_gpib_sad = address
    ip_address, gpib_pad, gpib_sad = _sanitize_address(address)

    assert (true_ip_address, true_gpib_pad, true_gpib_sad) == (ip_address, gpib_pad, gpib_sad)


bad_addresses = ["prologix://princeton.edu/1:Z",
                 "prologiz://princeton.edu/1",
                 "prologix://princeton..edu/1:123",
                 "princeton.edu/1:123",
                 "prologix://princeton.edu/1:121:1",
                 ]


@pytest.mark.parametrize("address", bad_addresses)
def test_sanitize_bad_address(address):
    with pytest.raises(RuntimeError):
        _sanitize_address(address)


def test_gpid_addr_format():
    test_object = PrologixGPIBObject("prologix://valid.name.edu/12")
    assert test_object._prologix_escape_characters('+11/.\x11\nlala\n\r') == '\x11+11/.\x11\x11\x11\nlala\x11\n\x11\r'
