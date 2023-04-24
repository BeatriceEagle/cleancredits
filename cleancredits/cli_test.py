import pytest
from click.testing import CliRunner

from .cli import mask
from .helpers_test import TESTDATA_PATH


@pytest.mark.parametrize(
    "hue_min,hue_max,sat_min,sat_max,val_min,val_max,grow,bbox_x1,bbox_x2,bbox_y1,bbox_y2",
    [
        (0, 179, 0, 255, 0, 255, 0, 0, None, 0, None),
        (10, 20, 30, 50, 40, 60, 1, 100, 500, 150, 700),
        (-5, 200, -10, 290, -50, 365, 500, 2000, 2000, 9001, 9001),
        (200, -5, 290, -10, 365, -50, -1, -20, -21, -200, -2000),
    ],
)
def test_mask_defaults(
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
    tmp_path,
):
    # There's enough logic here that it's worth just explicitly checking that
    # the values end up as expected.
    runner = CliRunner()
    result = runner.invoke(
        mask,
        [
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
            "--bbox-x1",
            bbox_x1,
            "--bbox-x2",
            bbox_x2,
            "--bbox-y1",
            bbox_y1,
            "--bbox-y2",
            bbox_y2,
        ],
        standalone_mode=False,
    )
    assert result.exception is None, result.output
    app = result.return_value
    assert app.hue_min.get() == max(min(hue_min, 179), 0)
    assert app.hue_max.get() == max(min(hue_max, 179), 0)
    assert app.sat_min.get() == max(min(sat_min, 255), 0)
    assert app.sat_max.get() == max(min(sat_max, 255), 0)
    assert app.val_min.get() == max(min(val_min, 255), 0)
    assert app.val_max.get() == max(min(val_max, 255), 0)
    assert app.grow.get() == max(min(grow, 20), 0)
    assert app.bbox_x1.get() == max(min(bbox_x1, app.video_width), 0)
    assert app.bbox_y1.get() == max(min(bbox_y1, app.video_height), 0)
    if bbox_x2 is None:
        assert app.bbox_x2.get() == app.video_width
    else:
        assert app.bbox_x2.get() == max(min(bbox_x2, app.video_width), 0)
    if bbox_x2 is None:
        assert app.bbox_y2.get() == app.video_height
    else:
        assert app.bbox_y2.get() == max(min(bbox_y2, app.video_height), 0)
