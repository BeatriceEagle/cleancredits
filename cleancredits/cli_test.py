import click
import pytest

from .cli import TIMECODE, FRAMERATE


def test_timecode_param_type__valid_timecode():
    value = "00:00:01"
    result = TIMECODE.convert(value, None, None)
    assert result == value


def test_timecode_param_type__valid_timecode__with_microseconds():
    value = "00:00:01.379"
    result = TIMECODE.convert(value, None, None)
    assert result == value


def test_timecode_param_type__invalid_timecode__word():
    value = "whatever"
    with pytest.raises(click.BadParameter):
        TIMECODE.convert(value, None, None)


def test_timecode_param_type__invalid_timecode__prefix():
    value = "prefix00:00:01"
    with pytest.raises(click.BadParameter):
        TIMECODE.convert(value, None, None)


def test_timecode_param_type__invalid_timecode__suffix():
    value = "00:00:01suffix"
    with pytest.raises(click.BadParameter):
        TIMECODE.convert(value, None, None)


def test_timecode_param_type__invalid_timecode__not_a_string():
    value = 5
    with pytest.raises(click.BadParameter):
        TIMECODE.convert(value, None, None)

def test_framerate_param_type__valid_framerate():
    value = "25"
    result = FRAMERATE.convert(value, None, None)
    assert result == value

def test_framerate_param_type__valid_framerate__int():
    value = 25
    result = FRAMERATE.convert(value, None, None)
    assert result == str(value)

def test_framerate_param_type__valid_framerate__int_ratio():
    value = "24000/1001"
    result = FRAMERATE.convert(value, None, None)
    assert result == value


def test_framerate_param_type__invalid_framerate__word():
    value = "whatever"
    with pytest.raises(click.BadParameter):
        FRAMERATE.convert(value, None, None)


def test_framerate_param_type__invalid_framerate__float():
    value = 23.976
    with pytest.raises(click.BadParameter):
        FRAMERATE.convert(value, None, None)


def test_framerate_param_type__invalid_framerate__float_string():
    value = "23.976"
    with pytest.raises(click.BadParameter):
        FRAMERATE.convert(value, None, None)
