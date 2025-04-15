import os
import pathlib
import re
import shutil

import click
import cv2

from .__version__ import __version__
from .gui.app import App
from .helpers import clean_frames, get_frame, join_frames, render_mask, split_frames
from .param_types import FRAMERATE, TIMECODE, timecode_to_frame

DEFAULT_RADIUS = 3


@click.group(invoke_without_command=True)
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is not None:
        return

    app = App()
    app.open_video()
    if not app.video_path:
        print("No video selected - exiting")
        return None
    app.build()
    app.mainloop()


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
    "input_mask_path",
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
    "--crop-left",
    help="Crop left",
    type=click.IntRange(0, clamp=True),
    default=0,
)
@click.option(
    "--crop-right",
    help="Crop right",
    type=click.IntRange(0, clamp=True),
    default=None,
)
@click.option(
    "--crop-top",
    help="Crop top",
    type=click.IntRange(0, clamp=True),
    default=0,
)
@click.option(
    "--crop-bottom",
    help="Crop bottom",
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
    input_mask_path,
    output,
    hue_min,
    hue_max,
    sat_min,
    sat_max,
    val_min,
    val_max,
    grow,
    crop_left,
    crop_right,
    crop_top,
    crop_bottom,
    gui,
):
    cap = cv2.VideoCapture(video)
    video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    crop_left = min(crop_left, video_width)
    if crop_right is None:
        crop_right = video_width
    else:
        crop_right = min(crop_right, video_width)
    crop_top = min(crop_top, video_height)
    if crop_bottom is None:
        crop_bottom = video_height
    else:
        crop_bottom = min(crop_bottom, video_height)

    fps = cap.get(cv2.CAP_PROP_FPS)
    start_frame = timecode_to_frame(start, fps, default=0)
    end_frame = timecode_to_frame(
        end, fps, default=cap.get(cv2.CAP_PROP_FRAME_COUNT) - 1
    )

    out_file = pathlib.Path(output)

    input_mask = None
    if input_mask_path:
        input_mask = cv2.imread(str(input_mask_path))
        input_mask = cv2.cvtColor(input_mask, cv2.COLOR_BGR2GRAY)

    frame = get_frame(cap, start_frame)
    mask = render_mask(
        image=frame,
        hue_min=hue_min,
        hue_max=hue_max,
        sat_min=sat_min,
        sat_max=sat_max,
        val_min=val_min,
        val_max=val_max,
        grow=grow,
        crop_left=crop_left,
        crop_right=crop_right,
        crop_top=crop_top,
        crop_bottom=crop_bottom,
        input_mask=input_mask,
    )
    cv2.imwrite(str(out_file), mask)
    return mask


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
    input_framerate = cap.get(cv2.CAP_PROP_FPS)
    if not framerate:
        # Default to the input video's framerate
        framerate = input_framerate

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

    start_frame = timecode_to_frame(start, fps=input_framerate, default=0)
    end_frame = timecode_to_frame(
        end, fps=input_framerate, default=cap.get(cv2.CAP_PROP_FRAME_COUNT) - 1
    )

    split_frames(
        video_file,
        clip_folder,
        start=f"{start_frame / input_framerate}s",
        end=f"{end_frame / input_framerate}s",
    )

    assert mask_file.is_file()
    mask_im = cv2.imread(str(mask_file), cv2.IMREAD_GRAYSCALE)
    _, mask_im = cv2.threshold(mask_im, 1, 255, cv2.THRESH_BINARY)
    for in_file, out_file in clean_frames(
        mask_im, clip_folder, output_clip_folder, radius
    ):
        print(in_file, out_file)

    if output:
        out_file = pathlib.Path(output)
        join_frames(output_clip_folder, out_file, framerate)
