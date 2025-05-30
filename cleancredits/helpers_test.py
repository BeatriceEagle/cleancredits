import os
import pathlib
import shutil

import cv2
import numpy as np
import pytest
from numpy.testing import assert_array_equal

from .helpers import clean_frames, join_frames, split_frames

FILE_PATH = pathlib.Path(__file__).resolve()
TESTDATA_PATH = FILE_PATH.parent / "testdata"


def test_split_frames(tmp_path):
    split_frames(TESTDATA_PATH / "horses-720p.mp4", tmp_path)
    frame_files = list(tmp_path.iterdir())
    assert len(frame_files) == 25


def test_split_frames__start_end_empty_string(tmp_path):
    split_frames(TESTDATA_PATH / "horses-720p.mp4", tmp_path, start="", end="")
    frame_files = list(tmp_path.iterdir())
    assert len(frame_files) == 25


def test_split_frames__start_end(tmp_path):
    split_frames(
        TESTDATA_PATH / "horses-720p.mp4",
        tmp_path,
        start="00:00:00.040",
        end="00:00:00.960",
    )
    frame_files = list(tmp_path.iterdir())
    assert len(frame_files) == 23


def test_clean_frames(tmp_path):
    in_dir = TESTDATA_PATH / "horses-720p"
    out_dir = tmp_path
    mask_file = TESTDATA_PATH / "horses-720p-mask.png"

    mask_im = cv2.imread(str(mask_file), cv2.IMREAD_GRAYSCALE)
    _, mask_im = cv2.threshold(mask_im, 1, 255, cv2.THRESH_BINARY)
    for _, _ in clean_frames(mask_im, in_dir, out_dir, 3):
        pass
    cleaned_frame_files = list(out_dir.iterdir())
    assert len(list(in_dir.iterdir())) == len(cleaned_frame_files)

    # Enforce an inverted threshold to cleanly remove the interpolation.
    mask_im = cv2.imread(str(mask_file), cv2.IMREAD_GRAYSCALE)
    _, mask_im = cv2.threshold(mask_im, 1, 255, cv2.THRESH_BINARY_INV)

    # Loop through the frames and assert that:
    # 1. They are not the same.
    # 2. If you remove the mask they are the same.
    for in_file in in_dir.iterdir():
        out_file = out_dir / in_file.name

        in_im = cv2.imread(str(in_file))
        out_im = cv2.imread(str(out_file))

        with pytest.raises(AssertionError):
            assert_array_equal(in_im, out_im)
        assert_array_equal(
            cv2.bitwise_and(in_im, in_im, mask=mask_im),
            cv2.bitwise_and(out_im, out_im, mask=mask_im),
        )


def test_join_frames(tmp_path):
    in_dir = TESTDATA_PATH / "horses-720p"
    out_file = tmp_path / "output.mp4"
    expected_framerate = 25
    assert not out_file.exists()
    join_frames(in_dir, out_file, expected_framerate)
    assert out_file.exists()
    assert out_file.is_file()
    cap = cv2.VideoCapture(str(out_file))
    framerate = cap.get(cv2.CAP_PROP_FPS)
    assert framerate == expected_framerate
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    expected_frame_count = len(
        [f for f in os.listdir(in_dir) if os.path.isfile(os.path.join(in_dir, f))]
    )
    assert frame_count == expected_frame_count


def test_join_frames__int_framerate(tmp_path):
    in_dir = TESTDATA_PATH / "horses-720p"
    out_file = tmp_path / "output.mp4"
    expected_framerate = 15
    assert not out_file.exists()
    join_frames(in_dir, out_file, expected_framerate)
    assert out_file.exists()
    assert out_file.is_file()
    cap = cv2.VideoCapture(str(out_file))
    framerate = cap.get(cv2.CAP_PROP_FPS)
    assert framerate == expected_framerate
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    expected_frame_count = len(
        [f for f in os.listdir(in_dir) if os.path.isfile(os.path.join(in_dir, f))]
    )
    assert frame_count == expected_frame_count


def test_join_frames__float_framerate(tmp_path):
    in_dir = TESTDATA_PATH / "horses-720p"
    out_file = tmp_path / "output.mp4"
    expected_framerate = 24000 / 1001
    assert not out_file.exists()
    join_frames(in_dir, out_file, "24000/1001")
    assert out_file.exists()
    assert out_file.is_file()
    cap = cv2.VideoCapture(str(out_file))
    framerate = cap.get(cv2.CAP_PROP_FPS)
    assert framerate == expected_framerate
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    expected_frame_count = len(
        [f for f in os.listdir(in_dir) if os.path.isfile(os.path.join(in_dir, f))]
    )
    assert frame_count == expected_frame_count


def test_join_frames__high_start_frame(tmp_path):
    in_dir = TESTDATA_PATH / "horses-720p-100"
    out_file = tmp_path / "output.mp4"
    expected_framerate = 15
    assert not out_file.exists()
    join_frames(in_dir, out_file, expected_framerate, start_frame=101)
    assert out_file.exists()
    assert out_file.is_file()
    cap = cv2.VideoCapture(str(out_file))
    framerate = cap.get(cv2.CAP_PROP_FPS)
    assert framerate == expected_framerate
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    expected_frame_count = len(
        [f for f in os.listdir(in_dir) if os.path.isfile(os.path.join(in_dir, f))]
    )
    assert frame_count == expected_frame_count
