import os
import pathlib
import re
import shutil

import click
import cv2

from .gui import HSVMaskGUI
from .helpers import clean_frames, join_frames, split_frames
from .param_types import FRAMERATE, TIMECODE, timecode_to_frame

DEFAULT_RADIUS = 3


@click.group()
def cli():
    pass


@cli.command(help="Generate a mask based on a video clip")
@click.argument(
    "video", type=click.Path(exists=True, dir_okay=False, resolve_path=True)
)
@click.option(
    "-s",
    "--start",
    help="Start timecode (HH:MM:SS[:frame]) in the input video",
    type=TIMECODE,
)
@click.option(
    "-e",
    "--end",
    help="End timecode (HH:MM:SS[:frame]) in the input video",
    type=TIMECODE,
)
@click.option(
    "-i",
    "--input",
    "input_mask",
    help="Input mask. These pixels will always be present in the output mask (unless explicitly excluded).",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
)
@click.option(
    "-o",
    "--output",
    help="Output mask to this location",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True),
    required=True,
)
def mask(video, start, end, input_mask, output):
    cap = cv2.VideoCapture(video)
    video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    start_frame = timecode_to_frame(start, fps, default=0)
    end_frame = timecode_to_frame(
        end, fps, default=cap.get(cv2.CAP_PROP_FRAME_COUNT) - 1
    )

    if input_mask:
        input_mask = pathlib.Path(input_mask)
    out_file = pathlib.Path(output)
    app = HSVMaskGUI(cap, start_frame, end_frame, out_file, input_mask)
    app.mainloop()


@cli.command()
@click.argument(
    "video", type=click.Path(exists=True, dir_okay=False, resolve_path=True)
)
@click.argument("mask", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option(
    "-s",
    "--start",
    help="Start timecode (HH:MM:SS[:frame]) in the input video",
    type=TIMECODE,
)
@click.option(
    "-e",
    "--end",
    help="End timecode (HH:MM:SS[:frame]) in the input video",
    type=TIMECODE,
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
    cap = cv2.VideoCapture(video)
    if not framerate:
        # Default to the input video's framerate
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

    start_frame = timecode_to_frame(start, fps=framerate, default=0)
    end_frame = timecode_to_frame(
        end, fps=framerate, default=cap.get(cv2.CAP_PROP_FRAME_COUNT) - 1
    )

    split_frames(
        video_file,
        clip_folder,
        start=f"{start_frame / framerate}s",
        end=f"{end_frame / framerate}s",
    )
    clean_frames(mask_file, clip_folder, output_clip_folder, radius)

    if output:
        out_file = pathlib.Path(output)
        join_frames(output_clip_folder, out_file, framerate)
