import math
import re

import click

VALID_TIMECODE_RE = re.compile(
    r"^(?P<hours>\d\d):(?P<minutes>\d\d):(?P<seconds>\d\d(\.\d+)?)(?::(?P<frames>\d\d))?$"
)
VALID_FRAMERATE_RE = re.compile(r"^\d+(?:/\d+)?$")


class TimecodeParamType(click.ParamType):
    name = "timecode"

    def convert(self, value, param, ctx):
        if isinstance(value, str) and VALID_TIMECODE_RE.match(value):
            return value
        self.fail(f"{value!r} must be a timecode in the format HH:MM:SS[:frame]", param, ctx)


TIMECODE = TimecodeParamType()


class FramerateParamType(click.ParamType):
    name = "framerate"

    def convert(self, value, param, ctx):
        if isinstance(value, str) and VALID_FRAMERATE_RE.match(value):
            return value
        if isinstance(value, int):
            return str(value)
        self.fail(
            f"{value!r} must be a framerate expressed as an integer or ratio of integers (for example 24000/1001 for 23.976fps)",
            param,
            ctx,
        )


FRAMERATE = FramerateParamType()


def timecode_to_frame(timecode, fps, default=None):
    if not timecode:
        return default
    times = VALID_TIMECODE_RE.match(timecode).groupdict(default=0)
    seconds = (
        float(times["seconds"])
        + (int(times["minutes"]) * 60)
        + (int(times["hours"]) * 60 * 60)
    )

    frame_num = math.floor(seconds * fps)
    if times['frames']:
        frame_num += int(times['frames'])
    return frame_num
