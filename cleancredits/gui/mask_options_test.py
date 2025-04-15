try:
    import tkinter as tk
except ModuleNotFoundError as exc:
    tk = None

from .mask_options import MaskOptions


def test_mask_options_build():
    root = tk.Tk()
    mask_options = MaskOptions(root, 100, 100, 100, 100, None)
    mask_options.build()
