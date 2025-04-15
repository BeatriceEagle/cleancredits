try:
    import tkinter as tk
except ModuleNotFoundError as exc:
    tk = None

from .render_options import RenderOptions


def test_render_options_build():
    root = tk.Tk()
    render_options = RenderOptions(root, "", 100, 25, 100, None)
    render_options.build()
