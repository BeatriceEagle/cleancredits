import os
import re
import shutil
import subprocess

import click
import cv2

VALID_TIMECODE_RE = re.compile(r"\d\d:\d\d:\d\d(\.\d+)?")


class TimecodeParamType(click.ParamType):
    name = "timecode"

    def convert(self, value, param, ctx):
        if isinstance(value, str) and VALID_TIMECODE_RE.match(value):
            return value
        self.fail("f{value}!r must be a timecode in the format HH:MM:SS", param, ctx)


TIMECODE = TimecodeParamType()


@click.command()
@click.argument(
    "video", type=click.Path(exists=True, dir_okay=False, resolve_path=True)
)
@click.argument("mask", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option(
    "-s", "--start", help="Start timecode (HH:MM:SS) in the input video", type=TIMECODE
)
@click.option(
    "-e", "--end", help="End timecode (HH:MM:SS) in the input video", type=TIMECODE
)
@click.option("-r", "--radius", default=3, help="Interpolation radius")
@click.option("-f", "--framerate", default=24)
@click.option(
    "-o",
    "--output",
    help="Convert frames to video and output to this location if set",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True),
)
def cli(video, mask, start, end, radius, framerate, output):
    basename = os.path.basename(video)
    stripped_name, _ = os.path.splitext(basename)

    cwd = os.getcwd()
    clip_folder = os.path.join(cwd, stripped_name)
    if os.path.exists(clip_folder):
        click.confirm(
            f"Clip folder ({clip_folder}) already exists; do you want to delete it and continue?",
            abort=True,
            prompt_suffix="",
        )
        shutil.rmtree(clip_folder)
    os.makedirs(clip_folder)

    export_frames_args = ["ffmpeg"]
    if start:
        export_frames_args += ["-ss", start]
    export_frames_args += ["-i", video]
    if end:
        export_frames_args += ["-to", end]
    export_frames_args += [
        "-r",
        f"{framerate}/1",
        f"{stripped_name}/%03d{stripped_name}.png",
    ]
    subprocess.run(export_frames_args)

    mask = cv2.imread(mask)
    mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    output_clip_folder = os.path.join(clip_folder, "output")
    os.chdir(clip_folder)
    files = sorted(os.listdir(clip_folder))
    os.mkdir(output_clip_folder)
    for f in files:
        print(f)
        orig = cv2.imread(f)
        orig = cv2.cvtColor(orig, cv2.COLOR_BGR2RGB)

        interp = cv2.inpaint(orig, mask, radius, cv2.INPAINT_TELEA)
        interp = cv2.cvtColor(interp, cv2.COLOR_BGR2RGB)
        interp = interp.astype(int)

        cv2.imwrite(os.path.join(output_clip_folder, f), interp)

    if output:
        subprocess.run(
            [
                "ffmpeg",
                "-framerate",
                f"{framerate}",
                "-i",
                os.path.join(output_clip_folder, f"%03d{stripped_name}.png"),
                "-vcodec",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                output,
            ],
        )
