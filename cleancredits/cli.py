import os
import pathlib
import re
import shutil
import tkinter as tk

import click
import cv2

from .gui import HSVMaskApp
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
@click.option(
    "--hue-min",
    help="Minimum hue",
    type=click.IntRange(0, 179, clamp=True),
    default=0,
)
@click.option(
    "--hue-max",
    help="Maximum hue",
    type=click.IntRange(0, 179, clamp=True),
    default=179,
)
@click.option(
    "--sat-min",
    help="Minimum saturation",
    type=click.IntRange(0, 255, clamp=True),
    default=0,
)
@click.option(
    "--sat-max",
    help="Maximum saturation",
    type=click.IntRange(0, 255, clamp=True),
    default=255,
)
@click.option(
    "--val-min",
    help="Minimum value",
    type=click.IntRange(0, 255, clamp=True),
    default=0,
)
@click.option(
    "--val-max",
    help="Maximum value",
    type=click.IntRange(0, 255, clamp=True),
    default=255,
)
@click.option(
    "--grow",
    help="Grow amount",
    type=click.IntRange(0, 20, clamp=True),
    default=0,
)
@click.option(
    "--bbox-x1",
    help="Bounding box left x",
    type=click.IntRange(0, clamp=True),
    default=0,
)
@click.option(
    "--bbox-x2",
    help="Bounding box right x",
    type=click.IntRange(0, clamp=True),
    default=None,
)
@click.option(
    "--bbox-y1",
    help="Bounding box top y",
    type=click.IntRange(0, clamp=True),
    default=0,
)
@click.option(
    "--bbox-y2",
    help="Bounding box bottom y",
    type=click.IntRange(0, clamp=True),
    default=None,
)
@click.option(
    "--gui/--no-gui",
    help="Set --no-gui to directly render the mask without displaying the GUI",
    default=True,
)
def mask(
    video,
    start,
    end,
    input_mask,
    output,
    hue_min,
    hue_max,
    sat_min,
    sat_max,
    val_min,
    val_max,
    grow,
    bbox_x1,
    bbox_x2,
    bbox_y1,
    bbox_y2,
    gui,
):
    cap = cv2.VideoCapture(video)
    video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    bbox_x1 = min(bbox_x1, video_width)
    if bbox_x2 is None:
        bbox_x2 = video_width
    else:
        bbox_x2 = min(bbox_x2, video_width)
    bbox_y1 = min(bbox_y1, video_height)
    if bbox_y2 is None:
        bbox_y2 = video_height
    else:
        bbox_y2 = min(bbox_y2, video_height)

    fps = cap.get(cv2.CAP_PROP_FPS)
    start_frame = timecode_to_frame(start, fps, default=0)
    end_frame = timecode_to_frame(
        end, fps, default=cap.get(cv2.CAP_PROP_FRAME_COUNT) - 1
    )

    root = tk.Tk()
    root.title("HSV Mask")

    options_size = 300
    root.geometry(f"{video_width + options_size}x{video_height}+0+0")
    root.minsize(video_width + options_size, video_height)

    if input_mask:
        input_mask = pathlib.Path(input_mask)
    out_file = pathlib.Path(output)
    app = HSVMaskApp(
        root,
        cap,
        start_frame,
        end_frame,
        out_file,
        hue_min,
        hue_max,
        sat_min,
        sat_max,
        val_min,
        val_max,
        grow,
        bbox_x1,
        bbox_x2,
        bbox_y1,
        bbox_y2,
        input_mask,
    )
    if gui:
        app.mainloop()
    else:
        app._cache_mask()
        app.save_and_quit()

    return app


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
