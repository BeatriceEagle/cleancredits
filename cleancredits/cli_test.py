import click
import pytest

from .cli import TIMECODE


def test_timecode_param_type__valid_timecode():
    value = "00:00:01"
    result = TIMECODE.convert(value, None, None)
    assert value == result


def test_timecode_param_type__valid_timecode__with_microseconds():
    value = "00:00:01.379"
    result = TIMECODE.convert(value, None, None)
    assert value == result


def test_timecode_param_type__invalid_timecode():
    value = "whatever"
    with pytest.raises(click.BadParameter):
        TIMECODE.convert(value, None, None)


def test_timecode_param_type__invalid_timecode__not_a_string():
    value = 5
    with pytest.raises(click.BadParameter):
        TIMECODE.convert(value, None, None)
