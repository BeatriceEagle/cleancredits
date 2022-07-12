import os
import pathlib
import re
import shutil
import tkinter as tk

import click
import cv2

from .helpers import clean_frames, join_frames, split_frames
from .gui import HSVMaskApp
from .param_types import FRAMERATE, TIMECODE, timecode_to_frame


DEFAULT_RADIUS = 3

@click.group()
def cli():
    pass


@cli.command()
@click.argument(
    "video", type=click.Path(exists=True, dir_okay=False, resolve_path=True)
)
@click.option(
    "-s", "--start", help="Start timecode (HH:MM:SS[:frame]) in the input video", type=TIMECODE
)
@click.option(
    "-e", "--end", help="End timecode (HH:MM:SS[:frame]) in the input video", type=TIMECODE
)
@click.option(
    "-o",
    "--output",
    help="Output mask to this location",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True),
    required=True,
)
def generate_hsv_mask(video, start, end, output):
    cap = cv2.VideoCapture(video)
    video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    start_frame = timecode_to_frame(start, fps, default=0)
    end_frame = timecode_to_frame(end, fps, default=cap.get(cv2.CAP_PROP_FRAME_COUNT) - 1)

    root = tk.Tk()
    root.title('HSV Mask')

    options_size = 300
    root.geometry(f'{video_width + options_size}x{video_height}+0+0')
    root.minsize(video_width+options_size, video_height)

    app = HSVMaskApp(root, cap, start_frame, end_frame, output)
    app.mainloop()


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
