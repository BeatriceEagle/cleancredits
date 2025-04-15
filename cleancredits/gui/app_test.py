try:
    import tkinter as tk
except ModuleNotFoundError as exc:
    tk = None

from .app import App


def test_app_build():
    root = tk.Tk()
    app = App()
    app.video_opened = True
    app.video_width = 100
    app.video_height = 100
    app.frame_count = 100
    app.framerate = 25
    app.zoom_factor_fit = 100
    app.cap = None
    app.build()
