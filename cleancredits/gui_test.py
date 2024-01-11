import pytest

from .gui import get_zoom_crop


@pytest.mark.parametrize(
    "zoom_factor,zoom_center_coords,video_dims,display_dims,expected_crop_coords,expected_zoom_dims",
    [
        # Zoom in - video width == display width
        [1.0, (0, 0), (1000, 1000), (1000, 1000), (0, 0), (1000, 1000)],
        [2.0, (0, 0), (1000, 1000), (1000, 1000), (0, 0), (500, 500)],
        [3.0, (0, 0), (1000, 1000), (1000, 1000), (0, 0), (333, 333)],
        [1.0, (1000, 1000), (1000, 1000), (1000, 1000), (0, 0), (1000, 1000)],
        [2.0, (1000, 1000), (1000, 1000), (1000, 1000), (500, 500), (500, 500)],
        [3.0, (1000, 1000), (1000, 1000), (1000, 1000), (667, 667), (333, 333)],
        [1.0, (0, 749), (1000, 1000), (1000, 1000), (0, 0), (1000, 1000)],
        [2.0, (0, 749), (1000, 1000), (1000, 1000), (0, 499), (500, 500)],
        [3.0, (0, 749), (1000, 1000), (1000, 1000), (0, 583), (333, 333)],
        [1.0, (749, 0), (1000, 1000), (1000, 1000), (0, 0), (1000, 1000)],
        [2.0, (749, 0), (1000, 1000), (1000, 1000), (499, 0), (500, 500)],
        [3.0, (749, 0), (1000, 1000), (1000, 1000), (583, 0), (333, 333)],
        # Zoom in - video width > display width
        [1.0, (0, 0), (1000, 1000), (100, 100), (0, 0), (100, 100)],
        [2.0, (0, 0), (1000, 1000), (100, 100), (0, 0), (50, 50)],
        [3.0, (0, 0), (1000, 1000), (100, 100), (0, 0), (33, 33)],
        [1.0, (1000, 1000), (1000, 1000), (100, 100), (900, 900), (100, 100)],
        [2.0, (1000, 1000), (1000, 1000), (100, 100), (950, 950), (50, 50)],
        [3.0, (1000, 1000), (1000, 1000), (100, 100), (967, 967), (33, 33)],
        [1.0, (0, 749), (1000, 1000), (100, 100), (0, 699), (100, 100)],
        [2.0, (0, 749), (1000, 1000), (100, 100), (0, 724), (50, 50)],
        [3.0, (0, 749), (1000, 1000), (100, 100), (0, 733), (33, 33)],
        [1.0, (749, 0), (1000, 1000), (100, 100), (699, 0), (100, 100)],
        [2.0, (749, 0), (1000, 1000), (100, 100), (724, 0), (50, 50)],
        [3.0, (749, 0), (1000, 1000), (100, 100), (733, 0), (33, 33)],
    ],
)
def test_get_zoom_and_crop__zoom_in__video_size_gte_display_size(
    zoom_factor: float,
    zoom_center_coords,
    video_dims,
    display_dims,
    expected_crop_coords,
    expected_zoom_dims,
):
    zoom_center_x, zoom_center_y = zoom_center_coords
    video_width, video_height = video_dims
    display_width, display_height = display_dims
    crop_x, crop_y, zoom_width, zoom_height = get_zoom_crop(
        zoom_factor,
        zoom_center_x,
        zoom_center_y,
        video_width,
        video_height,
        display_width,
        display_height,
    )
    assert (crop_x, crop_y) == expected_crop_coords
    assert (zoom_width, zoom_height) == expected_zoom_dims


@pytest.mark.parametrize(
    "zoom_factor,zoom_center_coords,video_dims,display_dims,expected_crop_coords,expected_zoom_dims",
    [
        [1.0, (0, 0), (100, 100), (1000, 1000), (0, 0), (100, 100)],
        [2.0, (0, 0), (100, 100), (1000, 1000), (0, 0), (100, 100)],
        [3.0, (0, 0), (100, 100), (1000, 1000), (0, 0), (100, 100)],
        [10.0, (0, 0), (100, 100), (1000, 1000), (0, 0), (100, 100)],
        [20.0, (0, 0), (100, 100), (1000, 1000), (0, 0), (50, 50)],
        [30.0, (0, 0), (100, 100), (1000, 1000), (0, 0), (33, 33)],
        [1.0, (100, 100), (100, 100), (1000, 1000), (0, 0), (100, 100)],
        [2.0, (100, 100), (100, 100), (1000, 1000), (0, 0), (100, 100)],
        [3.0, (100, 100), (100, 100), (1000, 1000), (0, 0), (100, 100)],
        [10.0, (100, 100), (100, 100), (1000, 1000), (0, 0), (100, 100)],
        [20.0, (100, 100), (100, 100), (1000, 1000), (50, 50), (50, 50)],
        [30.0, (100, 100), (100, 100), (1000, 1000), (67, 67), (33, 33)],
        [1.0, (0, 74), (100, 100), (1000, 1000), (0, 0), (100, 100)],
        [2.0, (0, 74), (100, 100), (1000, 1000), (0, 0), (100, 100)],
        [3.0, (0, 74), (100, 100), (1000, 1000), (0, 0), (100, 100)],
        [10.0, (0, 74), (100, 100), (1000, 1000), (0, 0), (100, 100)],
        [20.0, (0, 74), (100, 100), (1000, 1000), (0, 49), (50, 50)],
        [30.0, (0, 74), (100, 100), (1000, 1000), (0, 58), (33, 33)],
        [1.0, (74, 0), (100, 100), (1000, 1000), (0, 0), (100, 100)],
        [2.0, (74, 0), (100, 100), (1000, 1000), (0, 0), (100, 100)],
        [3.0, (74, 0), (100, 100), (1000, 1000), (0, 0), (100, 100)],
        [10.0, (74, 0), (100, 100), (1000, 1000), (0, 0), (100, 100)],
        [20.0, (74, 0), (100, 100), (1000, 1000), (49, 0), (50, 50)],
        [30.0, (74, 0), (100, 100), (1000, 1000), (58, 0), (33, 33)],
    ],
)
def test_get_zoom_and_crop__zoom_in__video_size_lt_display_size(
    zoom_factor: float,
    zoom_center_coords,
    video_dims,
    display_dims,
    expected_crop_coords,
    expected_zoom_dims,
):
    zoom_center_x, zoom_center_y = zoom_center_coords
    video_width, video_height = video_dims
    display_width, display_height = display_dims
    crop_x, crop_y, zoom_width, zoom_height = get_zoom_crop(
        zoom_factor,
        zoom_center_x,
        zoom_center_y,
        video_width,
        video_height,
        display_width,
        display_height,
    )
    assert (crop_x, crop_y) == expected_crop_coords
    assert (zoom_width, zoom_height) == expected_zoom_dims


@pytest.mark.parametrize(
    "zoom_factor,zoom_center_coords,video_dims,display_dims,expected_crop_coords,expected_zoom_dims",
    [
        # Zoom out - video width == display width
        [0.5, (0, 0), (1000, 1000), (1000, 1000), (0, 0), (1000, 1000)],
        [0.2, (0, 0), (1000, 1000), (1000, 1000), (0, 0), (1000, 1000)],
        [0.1, (0, 0), (1000, 1000), (1000, 1000), (0, 0), (1000, 1000)],
        [0.5, (1000, 1000), (1000, 1000), (1000, 1000), (0, 0), (1000, 1000)],
        [0.2, (1000, 1000), (1000, 1000), (1000, 1000), (0, 0), (1000, 1000)],
        [0.1, (1000, 1000), (1000, 1000), (1000, 1000), (0, 0), (1000, 1000)],
        # Zoom out - video width < display width
        [0.5, (0, 0), (100, 100), (1000, 1000), (0, 0), (100, 100)],
        [0.2, (0, 0), (100, 100), (1000, 1000), (0, 0), (100, 100)],
        [0.1, (0, 0), (100, 100), (1000, 1000), (0, 0), (100, 100)],
        [0.5, (100, 100), (100, 100), (1000, 1000), (0, 0), (100, 100)],
        [0.2, (100, 100), (100, 100), (1000, 1000), (0, 0), (100, 100)],
        [0.1, (100, 100), (100, 100), (1000, 1000), (0, 0), (100, 100)],
    ],
)
def test_get_zoom_and_crop__zoom_out__video_size_lte_display_size(
    zoom_factor: float,
    zoom_center_coords,
    video_dims,
    display_dims,
    expected_crop_coords,
    expected_zoom_dims,
):
    zoom_center_x, zoom_center_y = zoom_center_coords
    video_width, video_height = video_dims
    display_width, display_height = display_dims
    crop_x, crop_y, zoom_width, zoom_height = get_zoom_crop(
        zoom_factor,
        zoom_center_x,
        zoom_center_y,
        video_width,
        video_height,
        display_width,
        display_height,
    )
    assert (crop_x, crop_y) == expected_crop_coords
    assert (zoom_width, zoom_height) == expected_zoom_dims


@pytest.mark.parametrize(
    "zoom_factor,zoom_center_coords,video_dims,display_dims,expected_crop_coords,expected_zoom_dims",
    [
        [0.5, (0, 0), (1000, 1000), (100, 100), (0, 0), (200, 200)],
        [0.2, (0, 0), (1000, 1000), (100, 100), (0, 0), (500, 500)],
        [0.1, (0, 0), (1000, 1000), (100, 100), (0, 0), (1000, 1000)],
        [0.5, (1000, 1000), (1000, 1000), (100, 100), (800, 800), (200, 200)],
        [0.2, (1000, 1000), (1000, 1000), (100, 100), (500, 500), (500, 500)],
        [0.1, (1000, 1000), (1000, 1000), (100, 100), (0, 0), (1000, 1000)],
        [0.5, (0, 749), (1000, 1000), (100, 100), (0, 649), (200, 200)],
        [0.2, (0, 749), (1000, 1000), (100, 100), (0, 499), (500, 500)],
        [0.1, (0, 749), (1000, 1000), (100, 100), (0, 0), (1000, 1000)],
        [0.5, (749, 0), (1000, 1000), (100, 100), (649, 0), (200, 200)],
        [0.2, (749, 0), (1000, 1000), (100, 100), (499, 0), (500, 500)],
        [0.1, (749, 0), (1000, 1000), (100, 100), (0, 0), (1000, 1000)],
    ],
)
def test_get_zoom_and_crop__zoom_out__video_size_gt_display_size(
    zoom_factor: float,
    zoom_center_coords,
    video_dims,
    display_dims,
    expected_crop_coords,
    expected_zoom_dims,
):
    zoom_center_x, zoom_center_y = zoom_center_coords
    video_width, video_height = video_dims
    display_width, display_height = display_dims
    crop_x, crop_y, zoom_width, zoom_height = get_zoom_crop(
        zoom_factor,
        zoom_center_x,
        zoom_center_y,
        video_width,
        video_height,
        display_width,
        display_height,
    )
    assert (crop_x, crop_y) == expected_crop_coords
    assert (zoom_width, zoom_height) == expected_zoom_dims
