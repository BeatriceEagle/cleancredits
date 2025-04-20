import os
import pathlib
from operator import attrgetter

import cv2
import ffmpeg
import numpy as np

MASK_MODE_INCLUDE = "Include"
MASK_MODE_EXCLUDE = "Exclude"

SPLIT_FRAME_FILENAME = "frame-%03d.png"


def get_frame(cap, frame_num) -> np.array:
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
    _, frame = cap.read()
    if frame is None:
        raise Exception(f"Invalid frame: {frame_num}")
    return frame


def render_mask(
    image,
    hue_min: int,
    hue_max: int,
    sat_min: int,
    sat_max: int,
    val_min: int,
    val_max: int,
    grow: int,
    crop_left: int,
    crop_right: int,
    crop_top: int,
    crop_bottom: int,
) -> np.array:
    # Set up np arrays for lower/upper bounds for mask range
    hsv_min = np.array([hue_min, sat_min, val_min])
    hsv_max = np.array([hue_max, sat_max, val_max])

    frame_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hsv_mask = cv2.inRange(frame_hsv, hsv_min, hsv_max)

    # Modify the hsv_mask
    if grow > 0:
        kernel = np.ones((grow, grow), np.uint8)
        hsv_mask = cv2.dilate(hsv_mask, kernel, iterations=1)

    bbox_mask = np.zeros(hsv_mask.shape, np.uint8)
    bbox_mask[crop_top:crop_bottom, crop_left:crop_right] = 255
    mask = cv2.bitwise_and(hsv_mask, hsv_mask, mask=bbox_mask)

    return mask


def combine_masks(
    mode: str,
    top: np.array,
    bottom: np.array,
) -> np.array:
    if mode == MASK_MODE_INCLUDE:
        mask = top
        # Combine with base mask in bitwise_or to include the areas in both masks.
        if bottom is not None:
            mask = cv2.bitwise_or(mask, bottom)
    else:
        # Invert so that the selected areas are excluded from the mask instead of included.
        mask = cv2.bitwise_not(top)
        # Combine with base mask in bitwise_and to remove the areas in the current mask.
        if bottom is not None:
            mask = cv2.bitwise_and(mask, bottom)
    return mask


def split_frames(video_file: pathlib.Path, out_dir: pathlib.Path, start=None, end=None):
    """Convert a video to a directory of frame images"""
    assert out_dir.is_dir()
    assert video_file.is_file()
    assert video_file.exists()

    out = out_dir / SPLIT_FRAME_FILENAME
    kwargs = {}
    if start:
        kwargs["ss"] = start
    if end:
        kwargs["to"] = end
    ffmpeg.input(str(video_file), **kwargs).output(str(out)).run()


def clean_frames(
    mask_im: np.array, in_dir: pathlib.Path, out_dir: pathlib.Path, radius: int
) -> (pathlib.Path, pathlib.Path):
    """For each input frame, clean it based on the mask file"""
    assert in_dir.is_dir()
    assert out_dir.is_dir()

    paths = sorted(in_dir.iterdir(), key=attrgetter("name"))
    for in_file in paths:
        out_file = out_dir / in_file.name

        # Skip non-files (i.e. directories)
        if not in_file.is_file():
            continue

        orig = cv2.imread(str(in_file))
        orig = cv2.cvtColor(orig, cv2.COLOR_BGR2RGB)

        interp = cv2.inpaint(orig, mask_im, radius, cv2.INPAINT_TELEA)
        interp = cv2.cvtColor(interp, cv2.COLOR_BGR2RGB)
        interp = interp.astype(int)

        cv2.imwrite(str(out_file), interp)
        yield in_file, out_file


def join_frames(
    in_dir: pathlib.Path,
    out_file: pathlib.Path,
    framerate: str,
    frame_filename: str = SPLIT_FRAME_FILENAME,
    overwrite_output: bool = False,
):
    assert in_dir.is_dir()

    in_ = in_dir / frame_filename
    # Set the input & output framerates to the same value to avoid ffmpeg dropping
    # or duplicating frames to "fix" the speed change.
    stream = (
        ffmpeg.input(str(in_), framerate=framerate)
        .filter("fps", fps=framerate)
        .output(str(out_file), vcodec="libx264", pix_fmt="yuv420p", crf=17)
    )

    stream.run(overwrite_output=overwrite_output)
