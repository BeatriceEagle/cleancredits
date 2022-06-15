import os

import cv2
import ffmpeg

SPLIT_FRAME_FILENAME = "%03d-img.png"


def split_frames(video, out_dir, start=None, end=None):
    """Convert a video to a directory of frame images"""
    out = os.path.join(out_dir, SPLIT_FRAME_FILENAME)
    kwargs = {}
    if start:
        kwargs["ss"] = start
    if end:
        kwargs["to"] = end
    ffmpeg.input(video, **kwargs).output(out).run()


def clean_frames(mask_file, in_dir, out_dir, radius):
    """For each input frame, clean it based on the mask file"""
    mask = cv2.imread(mask_file)
    mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    files = sorted(os.listdir(in_dir))
    for f in files:
        in_file = os.path.join(in_dir, f)
        out_file = os.path.join(out_dir, f)

        # Skip non-files (i.e. directories)
        if not os.path.isfile(in_file):
            continue

        print(in_file)
        orig = cv2.imread(in_file)
        orig = cv2.cvtColor(orig, cv2.COLOR_BGR2RGB)

        interp = cv2.inpaint(orig, mask, radius, cv2.INPAINT_TELEA)
        interp = cv2.cvtColor(interp, cv2.COLOR_BGR2RGB)
        interp = interp.astype(int)

        cv2.imwrite(out_file, interp)


def join_frames(in_dir, output, framerate):
    in_ = os.path.join(in_dir, SPLIT_FRAME_FILENAME)
    ffmpeg.input(in_).output(
        output, vcodec="libx264", pix_fmt="yuv420p", framerate=framerate
    ).run()
