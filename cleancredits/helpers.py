import os
import pathlib
from operator import attrgetter

import cv2
import ffmpeg
import numpy as np

SPLIT_FRAME_FILENAME = "frame-%03d.png"


def get_frame(cap, frame_num):
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
    bbox_x1: int,
    bbox_x2: int,
    bbox_y1: int,
    bbox_y2: int,
    input_mask=None,
    draw_mask=None,
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
    bbox_mask[bbox_y1:bbox_y2, bbox_x1:bbox_x2] = 255
    mask = cv2.bitwise_and(hsv_mask, hsv_mask, mask=bbox_mask)

    # Combine with base mask in bitwise_or
    if input_mask is not None:
        mask = cv2.bitwise_or(mask, input_mask)

    # Combine with include/exclude masks
    if draw_mask is not None:
        _, include_mask = cv2.threshold(draw_mask, 128, 255, cv2.THRESH_BINARY)
        mask = cv2.bitwise_or(mask, include_mask)
        _, exclude_mask = cv2.threshold(draw_mask, 126, 255, cv2.THRESH_BINARY)
        mask = cv2.bitwise_and(mask, exclude_mask)

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
    mask_file: pathlib.Path, in_dir: pathlib.Path, out_dir: pathlib.Path, radius: int
):
    """For each input frame, clean it based on the mask file"""
    assert mask_file.is_file()
    assert in_dir.is_dir()
    assert out_dir.is_dir()

    mask_im = cv2.imread(str(mask_file), cv2.IMREAD_GRAYSCALE)
    _, mask_im = cv2.threshold(mask_im, 1, 255, cv2.THRESH_BINARY)
    paths = sorted(in_dir.iterdir(), key=attrgetter("name"))
    for in_file in paths:
        out_file = out_dir / in_file.name

        # Skip non-files (i.e. directories)
        if not in_file.is_file():
            continue

        print(in_file)
        orig = cv2.imread(str(in_file))
        orig = cv2.cvtColor(orig, cv2.COLOR_BGR2RGB)

        interp = cv2.inpaint(orig, mask_im, radius, cv2.INPAINT_TELEA)
        interp = cv2.cvtColor(interp, cv2.COLOR_BGR2RGB)
        interp = interp.astype(int)

        cv2.imwrite(str(out_file), interp)


def join_frames(
    in_dir: pathlib.Path, out_file: pathlib.Path, input_framerate: float, framerate: str
):
    assert in_dir.is_dir()

    in_ = in_dir / SPLIT_FRAME_FILENAME
    # Set the input framerate explicitly to avoid using the default (25) which
    # may cause frames to be dropped or introduced if that doesn't match
    # the video being cleaned.
    ffmpeg.input(str(in_), framerate=input_framerate).filter(
        "fps", fps=framerate
    ).output(str(out_file), vcodec="libx264", pix_fmt="yuv420p", crf=17).run()
