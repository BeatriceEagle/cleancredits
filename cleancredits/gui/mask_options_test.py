import numpy as np
import pytest

try:
    import tkinter as tk
    from tkinter import ttk
except ModuleNotFoundError as exc:
    tk = None
    ttk = None

from ..helpers import MASK_MODE_INCLUDE
from .mask_options import LayerSelector, MaskOptions
from .video_display import MASK_SETTINGS, VideoDisplay


def test_mask_options_build():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter not supported")
    mask_options = MaskOptions(root, 100, 100, 100, 100, None)
    mask_options.build()


def test_layer_selector__save_layer():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter not supported")
    mask_options = MaskOptions(root, 100, 100, 100, 100, None)
    mask = object()
    options = {
        "mask_frame_number": 100,
        "mask_mode": MASK_MODE_INCLUDE,
        "hue_min": 50,
        "hue_max": 100,
        "sat_min": 50,
        "sat_max": 100,
        "val_min": 50,
        "val_max": 100,
        "grow": 1,
        "crop_left": 100,
        "crop_top": 200,
        "crop_right": 100,
        "crop_bottom": 200,
    }
    mask_options.set_options(options)
    options |= {"mask": mask, "input_mask": None}
    layer_selector = LayerSelector(ttk.Frame(root), "text", mask_options)
    layer_selector.save_layer(0, mask)
    assert len(layer_selector.layers) == 1
    assert layer_selector.layers[0] == options


def test_layer_selector__add_layer():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter not supported")
    mask_options = MaskOptions(root, 100, 100, 100, 100, None)
    mask = object()
    mask_options.set_options(
        {
            "mask_frame_number": 100,
        }
    )
    options = {
        k: v
        for k, v in mask_options.get_default_options().items()
        if k in MASK_SETTINGS
    } | {"mask_frame_number": 100}
    layer_selector = LayerSelector(ttk.Frame(root), "text", mask_options)
    layer_selector.save_layer(0, mask)
    layer_selector.add_layer()
    assert len(layer_selector.layers) == 2
    assert layer_selector.layers[0]["mask"] == mask
    assert layer_selector.layers[1] == options


def test_layer_selector__load_layer():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter not supported")
    mask_options = MaskOptions(root, 100, 100, 100, 100, None)
    layer_selector = LayerSelector(ttk.Frame(root), "text", mask_options)
    layer_selector.layers = [
        {
            "mask_frame_number": 100,
            "mask_mode": MASK_MODE_INCLUDE,
            "hue_min": 50,
            "hue_max": 100,
            "sat_min": 50,
            "sat_max": 100,
            "val_min": 50,
            "val_max": 100,
            "grow": 1,
            "crop_left": 100,
            "crop_top": 200,
            "crop_right": 100,
            "crop_bottom": 200,
            "mask": np.array([[1, 0], [0, 1]]),
        },
        {
            "mask_frame_number": 100,
            "mask_mode": MASK_MODE_INCLUDE,
            "hue_min": 50,
            "hue_max": 100,
            "sat_min": 50,
            "sat_max": 100,
            "val_min": 50,
            "val_max": 100,
            "grow": 1,
            "crop_left": 100,
            "crop_top": 200,
            "crop_right": 100,
            "crop_bottom": 200,
            "mask": np.array([[0, 0], [1, 1]]),
        },
        {
            "mask_frame_number": 100,
            "mask_mode": MASK_MODE_INCLUDE,
            "hue_min": 50,
            "hue_max": 100,
            "sat_min": 50,
            "sat_max": 100,
            "val_min": 50,
            "val_max": 100,
            "grow": 1,
            "crop_left": 100,
            "crop_top": 200,
            "crop_right": 100,
            "crop_bottom": 200,
            "mask": np.array([[1, 1], [1, 1]]),
        },
    ]
    layer_selector.load_layer(2)
    assert layer_selector.selected_index == 2
    np.testing.assert_array_equal(
        layer_selector.layers[2]["input_mask"], np.array([[1, 0], [1, 1]])
    )
    expected_options = layer_selector.layers[2].copy()
    del expected_options["mask"]
    expected_input_mask = expected_options.pop("input_mask")
    options = {
        k: v for k, v in mask_options.get_options().items() if k in MASK_SETTINGS
    }
    input_mask = options.pop("input_mask")
    assert options == expected_options
    np.testing.assert_array_equal(input_mask, expected_input_mask)
