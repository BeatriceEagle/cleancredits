import os
import pathlib
from operator import attrgetter

import cv2
import ffmpeg

SPLIT_FRAME_FILENAME = "frame-%03d.png"


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


def join_frames(in_dir: pathlib.Path, out_file: pathlib.Path, framerate):
    assert in_dir.is_dir()

    in_ = in_dir / SPLIT_FRAME_FILENAME
    ffmpeg.input(str(in_)).output(
        str(out_file), vcodec="libx264", pix_fmt="yuv420p", framerate=framerate
    ).run()
