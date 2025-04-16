import copy
import math
import pathlib
import sys
import tempfile

try:
    import tkinter as tk
    from tkinter import colorchooser, filedialog, messagebox, ttk
except ModuleNotFoundError as exc:
    tk = None
    colorchooser = None
    ttk = None

import cv2
import numpy as np
from PIL import Image, ImageTk

from ..helpers import clean_frames, get_frame, join_frames, render_mask, split_frames
from .mask_options import MaskOptions
from .render_options import RenderOptions
from .video_display import VideoDisplay


class App(object):
    options_size = 300
    section_padding = {"pady": (50, 0)}

    def __init__(self):
        self.video_path = None
        self.video_opened = False
        if tk is None:
            raise RuntimeError(
                "Could not initialize GUI. Python is not configured to support tkinter."
            )

    def open_video(self):
        self.video_path = filedialog.askopenfilename(
            title="Choose video file",
        )
        if not self.video_path:
            return
        # Set up the video capture here so that we validate that it can actually be opened,
        # and pass relevant data to widgets.
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            messagebox.showerror(
                title="cleancredits", message=f"Invalid video file: {self.video_path}"
            )
            return
        self.video_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.video_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_count = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
        self.framerate = self.cap.get(cv2.CAP_PROP_FPS)

        # Default zoom_factor to fit within a 720x480 window
        height_ratio = 480.0 / self.video_height
        width_ratio = 720.0 / self.video_width
        self.zoom_factor_fit = max(1, min(height_ratio, width_ratio) * 100)

        self.video_opened = True

    def build(self):
        if not self.video_opened:
            raise RuntimeError("Must call open_video before build")

        self.root = tk.Tk()
        self.root.title("cleancredits")

        self.root_container = ttk.Frame(self.root)
        self.video_container = ttk.Frame(self.root_container, width=720, height=480)
        # self.video_container.grid_propagate(0)
        self.video_display = VideoDisplay(
            parent=self.video_container,
            cap=self.cap,
            video_width=self.video_width,
            video_height=self.video_height,
        )
        self.left_sidebar = ttk.Frame(self.root_container)
        self.tabs = ttk.Notebook(self.left_sidebar)
        self.mask_tab = ttk.Frame(self.tabs)
        self.render_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.mask_tab, text="Mask", sticky="nsew")
        self.tabs.add(self.render_tab, text="Render", sticky="nsew")
        self.tabs.bind("<<NotebookTabChanged>>", self.handle_tab_change)

        self.mask_options = MaskOptions(
            self.mask_tab,
            self.video_width,
            self.video_height,
            self.frame_count,
            self.zoom_factor_fit,
            self.video_display,
        )
        self.mask_options.build()
        self.render_options = RenderOptions(
            self.render_tab,
            self.video_path,
            self.frame_count,
            self.framerate,
            self.zoom_factor_fit,
            self.video_display,
        )
        self.render_options.build()

        self.root_container.grid(column=0, row=0, sticky="nsew")
        self.video_container.grid(column=1, row=0, sticky="nsew", pady=20, padx=(0, 20))
        self.video_display.grid(column=0, row=0, sticky="nsew")
        self.left_sidebar.grid(column=0, row=0, sticky="nsew")
        self.tabs.grid(column=0, row=0, sticky="nsew")

    def mainloop(self):
        self.root.mainloop()

    def handle_tab_change(self, val=None):
        if self.tabs.tab(self.tabs.select(), option="text") == "Mask":
            self.mask_options.handle_selected()
        else:
            self.render_options.handle_selected()
