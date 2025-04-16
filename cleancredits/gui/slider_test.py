import pytest

try:
    import tkinter as tk
except ModuleNotFoundError as exc:
    tk = None

from .slider import Slider


@pytest.mark.parametrize(
    "newval,want",
    [
        ("", True),
        ("0", True),
        ("0.", False),
        ("0.0", False),
        ("1.", False),
        ("1.0", False),
        ("10.0", False),
        ("10.01", False),
        ("50", True),
        ("51", False),
    ],
)
def test_int_slider__validate(newval, want):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter not supported")
    variable = tk.IntVar()
    slider = Slider(
        root,
        label_text="label",
        from_=0,
        to=50,
        variable=variable,
    )
    assert slider.validate(newval) == want


@pytest.mark.parametrize(
    "val,want_textvariable",
    [
        ("0", "0"),
        ("0.", "0"),
        ("0.0", "0"),
        ("1.", "1"),
        ("1.1", "1"),
        ("50", "50"),
    ],
)
def test_int_slider__handle_change(val, want_textvariable):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter not supported")
    variable = tk.IntVar()
    slider = Slider(
        root,
        label_text="label",
        from_=0,
        to=50,
        variable=variable,
    )
    slider.variable.set(val)
    slider.handle_change()
    assert slider.textvariable.get() == want_textvariable


@pytest.mark.parametrize(
    "val,want_variable",
    [
        ("", 27),
        ("0", 0),
        ("0.", 27),
        ("0.0", 27),
        ("00", 0),
        ("1.", 27),
        ("1.1", 27),
        ("1.23", 27),
        ("1.234", 27),
        ("10.0", 27),
        ("10.01", 27),
        ("50", 50),
        ("500", 27),
    ],
)
def test_int_slider__handle_textvariable_change(val, want_variable):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter not supported")
    variable = tk.IntVar(value=27)
    slider = Slider(
        root,
        label_text="label",
        from_=0,
        to=50,
        variable=variable,
    )
    slider.textvariable.set(val)
    assert slider.variable.get() == want_variable


@pytest.mark.parametrize(
    "newval,want",
    [
        ("", True),
        ("0", True),
        ("0.", True),
        ("0.0", True),
        ("1.", True),
        ("1.0", True),
        ("10.0", True),
        ("10.01", True),
        ("50", True),
        ("50.0", True),
        ("50.1", False),
        ("51", False),
    ],
)
def test_float_slider_validate(newval, want):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter not supported")
    variable = tk.DoubleVar()
    slider = Slider(
        root,
        label_text="label",
        from_=0,
        to=50,
        variable=variable,
    )


@pytest.mark.parametrize(
    "val,want_textvariable",
    [
        ("0", "0"),
        ("0.0", "0"),
        ("1.0", "1"),
        ("1.1", "1.1"),
        ("1.23", "1.23"),
        ("10.0", "10"),
        ("10.01", "10.01"),
        ("50", "50"),
    ],
)
def test_float_slider__handle_change(val, want_textvariable):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter not supported")
    variable = tk.DoubleVar()
    slider = Slider(
        root,
        label_text="label",
        from_=0,
        to=50,
        variable=variable,
    )
    slider.variable.set(val)
    slider.handle_change()
    assert slider.textvariable.get() == want_textvariable


@pytest.mark.parametrize(
    "val,want_variable",
    [
        ("", 27),
        ("0", 0),
        ("0.", 0),
        ("0.0", 0),
        ("00", 0),
        ("1.", 1),
        ("1.1", 1.1),
        ("1.23", 1.23),
        ("1.234", 27),
        ("10.0", 10),
        ("10.01", 10.01),
        ("50", 50),
        ("50.0", 50),
        ("50.1", 27),
        ("500", 27),
    ],
)
def test_float_slider__handle_textvariable_change(val, want_variable):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter not supported")
    variable = tk.DoubleVar(value=27)
    slider = Slider(
        root,
        label_text="label",
        from_=0,
        to=50,
        variable=variable,
    )
    slider.textvariable.set(val)
    assert slider.variable.get() == want_variable
