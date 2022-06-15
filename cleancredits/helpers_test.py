import pathlib

from .helpers import split_frames

FILE_PATH = pathlib.Path(__file__).resolve()
TESTDATA_PATH = FILE_PATH.parent / "testdata"
HORSES_720P_PATH = TESTDATA_PATH / "horses-720p.mp4"


def test_split_frames(tmp_path):
    split_frames(HORSES_720P_PATH, tmp_path)
    frame_files = list(tmp_path.iterdir())
    assert len(frame_files) == 25


def test_split_frames__start_end_empty_string(tmp_path):
    split_frames(HORSES_720P_PATH, tmp_path, start="", end="")
    frame_files = list(tmp_path.iterdir())
    assert len(frame_files) == 25


def test_split_frames__start_end(tmp_path):
    split_frames(HORSES_720P_PATH, tmp_path, start="00:00:00.040", end="00:00:00.960")
    frame_files = list(tmp_path.iterdir())
    assert len(frame_files) == 23
