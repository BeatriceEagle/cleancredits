import pathlib

import cv2
import numpy as np

from .param_types import timecode_to_frame


def unchanged_pixels_mask(video, start, end, threshold, dilate, out_file: pathlib.Path):
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    start_frame = timecode_to_frame(start, fps, default=0)
    end_frame = timecode_to_frame(end, fps, default=cv2.CAP_PROP_FRAME_COUNT - 1)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    mask_im = None

    while cap.isOpened() and cap.get(cv2.CAP_PROP_POS_FRAMES) <= end_frame:
        _, frame = cap.read()
        if frame is None:
            break

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if mask_im is None:
            mask_im = frame
            continue

        mask_im = cv2.bitwise_and(mask_im, frame)

    _, mask_im = cv2.threshold(mask_im, threshold, 255, cv2.THRESH_BINARY)

    kernel = np.ones((dilate, dilate), np.uint8)
    mask_im = cv2.dilate(mask_im, kernel, iterations=1)
    cv2.imwrite(str(out_file), mask_im)
