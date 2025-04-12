import cv2
import pytest
from click.testing import CliRunner
from numpy.testing import assert_array_equal

from .cli import mask
from .helpers_test import TESTDATA_PATH


@pytest.mark.parametrize(
    "hue_min,hue_max,sat_min,sat_max,val_min,val_max,grow,crop_left,crop_right,crop_top,crop_bottom,input_mask",
    [
        (0, 179, 0, 255, 0, 255, 0, 0, None, 0, None, None),
        (10, 20, 30, 50, 40, 60, 1, 100, 500, 150, 700, None),
        (-5, 200, -10, 290, -50, 365, 500, 2000, 2000, 9001, 9001, None),
        (200, -5, 290, -10, 365, -50, -1, -20, -21, -200, -2000, None),
        (30, 60, 20, 200, 0, 240, 3, 20, 900, 35, 500, None),
        (0, 179, 0, 45, 221, 255, 2, 302, 762, 593, 678, None),
        (21, 87, 11, 143, 49, 109, 0, 588, 985, 455, 709, None),
        (-5, 200, -10, 290, -50, 365, 500, 2000, 2000, 9001, 9001, "horses-720p-mask"),
    ],
)
def test_mask_no_gui(
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
    input_mask,
    tmp_path,
):
    # Run through a few basic scenarios
    args = [
        f"{TESTDATA_PATH / 'horses-720p.mp4'}",
        f"--output={tmp_path / 'mask.png'}",
        "--no-gui",
        "--hue-min",
        hue_min,
        "--hue-max",
        hue_max,
        "--sat-min",
        sat_min,
        "--sat-max",
        sat_max,
        "--val-min",
        val_min,
        "--val-max",
        val_max,
        "--grow",
        grow,
        "--crop-left",
        crop_left,
        "--crop-top",
        crop_top,
    ]

    if crop_right is not None:
        args += [
            "--crop-right",
            crop_right,
        ]
    if crop_bottom is not None:
        args += [
            "--crop-bottom",
            crop_bottom,
        ]
    if input_mask is not None:
        args += ["-i", f"{TESTDATA_PATH / input_mask}.png"]

    runner = CliRunner()
    result = runner.invoke(
        mask,
        args,
        standalone_mode=False,
    )
    assert result.exception is None, result.output
    ret_mask = result.return_value

    expected_mask_path = str(
        TESTDATA_PATH
        / "horses-720p-masks"
        / f"mask-{hue_min}-{hue_max}-{sat_min}-{sat_max}-{val_min}-{val_max}-{grow}-{crop_left}-{crop_right}-{crop_top}-{crop_bottom}-{input_mask}.png"
    )
    expected_mask = cv2.imread(expected_mask_path)
    expected_mask = cv2.cvtColor(expected_mask, cv2.COLOR_BGR2GRAY)

    assert_array_equal(ret_mask, expected_mask)
