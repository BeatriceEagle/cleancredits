import os
import pathlib
import re
import shutil

import click
import cv2

from .helpers import clean_frames, join_frames, split_frames
from .mask import unchanged_pixels_mask
from .param_types import FRAMERATE, TIMECODE

DEFAULT_RADIUS = 3


@click.group()
def cli():
    pass


@cli.command()
@click.argument(
    "video", type=click.Path(exists=True, dir_okay=False, resolve_path=True)
)
@click.option(
    "-s", "--start", help="Start timecode (HH:MM:SS) in the input video", type=TIMECODE
)
@click.option(
    "-e", "--end", help="End timecode (HH:MM:SS) in the input video", type=TIMECODE
)
@click.option("-t", "--threshold", help="Sensitivity threshold (1-255)", default=127)
@click.option(
    "-d",
    "--dilate",
    help="Amount to 'dilate' (grow) the selected area of the mask",
    default=0,
)
@click.option(
    "-o",
    "--output",
    help="Convert frames to video and output to this location if set",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True),
    required=True,
)
def generate_mask(video, start, end, threshold, dilate, output):
    out_file = pathlib.Path(output)
    unchanged_pixels_mask(video, start, end, threshold, dilate, out_file)


@cli.command()
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
@click.option(
    "-r",
    "--radius",
    default=DEFAULT_RADIUS,
    help=f"Interpolation radius. Default: {DEFAULT_RADIUS}",
)
@click.option(
    "-f",
    "--framerate",
    type=FRAMERATE,
    help="Output framerate. Default: input framerate.",
)
@click.option(
    "-o",
    "--output",
    help="Convert frames to video and output to this location if set",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True),
)
def clean(video, mask, start, end, radius, framerate, output):
    if not framerate:
        # Default to the input video's framerate
        cap = cv2.VideoCapture(video)
        framerate = cap.get(cv2.CAP_PROP_FPS)

    video_file = pathlib.Path(video)
    mask_file = pathlib.Path(mask)

    cwd = pathlib.Path.cwd()
    clip_folder = cwd / video_file.stem
    if clip_folder.exists():
        click.confirm(
            f"Clip folder ({clip_folder}) already exists; do you want to delete it and continue?",
            abort=True,
            prompt_suffix="",
        )
        shutil.rmtree(clip_folder)
    os.makedirs(clip_folder)
    output_clip_folder = clip_folder / "output"
    os.mkdir(output_clip_folder)

    split_frames(video_file, clip_folder, start=start, end=end)
    clean_frames(mask_file, clip_folder, output_clip_folder, radius)

    if output:
        out_file = pathlib.Path(output)
        join_frames(output_clip_folder, out_file, framerate)
