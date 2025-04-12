import copy
import math
import pathlib
import sys
import tempfile

try:
    import tkinter as tk
    from tkinter import colorchooser, filedialog, ttk
except ModuleNotFoundError as exc:
    tk = None
    colorchooser = None
    ttk = None

import cv2
import numpy as np
from PIL import Image, ImageTk

from .helpers import clean_frames, get_frame, join_frames, render_mask, split_frames

DISPLAY_MODE_MASK = "Mask"
DISPLAY_MODE_PREVIEW = "Preview"
DISPLAY_MODE_ORIGINAL = "Original"

COLORCHOOSER_FUZZ = 10

DRAW_MODE_NONE = "None"
DRAW_MODE_EXCLUDE = "Exclude"
DRAW_MODE_INCLUDE = "Include"
DRAW_MODE_RESET = "Reset"


def get_screen_size(window):
    """get_screen_size returns the (width, height) of the screen the window is currently on"""
    toplevel = tk.Toplevel(window)
    toplevel.geometry(window.geometry())
    toplevel.update_idletasks()
    toplevel.attributes("-fullscreen", True)
    toplevel.state("iconic")
    width, height = toplevel.geometry().split("+")[0].split("x")
    toplevel.destroy()
    toplevel.update()
    return width, height


def get_zoom_crop(
    zoom_factor: float,
    zoom_center_x: int,
    zoom_center_y: int,
    video_width: int,
    video_height: int,
    display_width: int,
    display_height: int,
) -> (int, int, int, int):
    # zoom width and height are the dimensions of the box in the original
    # image that will be zoomed in (or out) and shown to the user. This should
    # be the largest possible width/height that will fit in the display box
    # after the zoom is applied.
    zoom_width = int(min(video_width * zoom_factor, display_width) / zoom_factor)
    zoom_height = int(min(video_height * zoom_factor, display_height) / zoom_factor)

    # Crop x and y are set at half the zoom width away from the zoom center,
    # in order to center it. However, the zoom center may be near an edge, so
    # we need to clip it between 0 and the farthest right point possible that
    # won't spill over the video width. If the entire frame should be visible,
    # the crop x and y will always be 0.
    crop_x = np.clip(
        zoom_center_x - (zoom_width // 2), 0, max(video_width - zoom_width, 0)
    )
    crop_y = np.clip(
        zoom_center_y - (zoom_height // 2),
        0,
        max(video_height - zoom_height, 0),
    )

    return crop_x, crop_y, zoom_width, zoom_height


def handle_scale_release(scale, callback):
    scale.bind("<ButtonRelease-1>", callback)


class GUI(object):
    options_size = 300
    section_padding = {"pady": (50, 0)}

    def __init__(self):
        self.input_mask = None
        # TODO: Make radius configurable
        self.inpaint_radius = 3
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
        self.cap = cv2.VideoCapture(self.video_path)
        self.video_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.video_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.start_frame = 0
        self.end_frame = self.cap.get(cv2.CAP_PROP_FRAME_COUNT) - 1
        self.framerate = self.cap.get(cv2.CAP_PROP_FPS)
        self.draw_mask = np.full((self.video_height, self.video_width), 127, np.uint8)

    def build(self):
        self.root = tk.Tk()
        self.root.title("cleancredits")
        self.root.minsize(2 * self.options_size, self.options_size)
        self.root.maxsize(*get_screen_size(self.root))
        self.root.resizable(True, True)

        self.style = ttk.Style()
        self.style.configure("Video.TFrame")
        self.style.configure("Options.TFrame")
        self.style.configure("Main.TFrame")

        self.frame = ttk.Frame(self.root, style="Main.TFrame")
        self.frame.pack(fill="both", expand=True)

        # Set up left sidebar first so that it will not shrink when we add the video.
        self.build_left_sidebar()
        self.build_video_display()

        # First render is basically a frame change.
        # Temporarily assume the display width / height match the video size
        # so that we can get accurate measurements.
        self.display_width = self.video_width
        self.display_height = self.video_height
        self.handle_mask_frame_change()

        # This will give us the actual window size.
        self.root.update()
        # Now set zoom factor to fit the whole image, then re-render.
        self.display_width = self.display.winfo_width()
        self.display_height = self.display.winfo_height()
        height_ratio = self.display_height / self.video_height
        width_ratio = self.display_width / self.video_width
        self.zoom_factor.set(max(1, int(min(height_ratio, width_ratio) * 100)))
        self.display.bind("<Configure>", self.handle_display_configure)

    def build_left_sidebar(self):
        self.left_sidebar = ttk.Frame(self.frame, style="Options.TFrame")
        self.left_sidebar.pack(side="left", fill="y")

        self.tabs = ttk.Notebook(self.left_sidebar)
        self.tabs.pack(side="left", fill="y")
        self.mask_tab = ttk.Frame(self.tabs)
        self.render_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.mask_tab, text="Mask", sticky="nsew")
        self.tabs.add(self.render_tab, text="Render", sticky="nsew")
        self.build_mask_tab()
        self.build_render_tab()
        self.tabs.bind("<<NotebookTabChanged>>", self.handle_tab_change)

    def build_mask_tab(self):
        self.mask_tab.rowconfigure(index=0, weight=1)
        self.mask_tab.columnconfigure(index=0, weight=5)
        self.mask_tab.columnconfigure(index=1, weight=1)

        self.mask_canvas = tk.Canvas(self.mask_tab)
        self.mask_canvas.grid(row=0, column=0, sticky="nsew")
        self.mask_scrollbar = ttk.Scrollbar(
            self.mask_tab, command=self.mask_canvas.yview
        )
        self.mask_canvas.config(yscrollcommand=self.mask_scrollbar.set)
        self.mask_scrollbar.grid(row=0, column=1, sticky="nsew")

        self.mask_canvas.rowconfigure(index=0, weight=1)
        self.mask_canvas.columnconfigure(index=0, weight=1)

        self.mask_options = ttk.Frame(self.mask_canvas)
        self.mask_options.grid(row=0, column=0, sticky="nsew")

        self.mask_options.rowconfigure(index=0, weight=1)
        self.mask_options.columnconfigure(0, weight=1)
        self.mask_options.columnconfigure(1, weight=4)

        self.mask_canvas.create_window(0, 0, window=self.mask_options, anchor=tk.NW)
        self.mask_canvas.configure(yscrollcommand=self.mask_scrollbar.set)

        # Change canvas size when widgets are added to the inner frame
        self.mask_options.bind(
            "<Configure>",
            lambda e: self.mask_canvas.configure(
                scrollregion=self.mask_canvas.bbox("all")
            ),
        )
        self.mask_frame = tk.IntVar()
        self.mask_frame.set(self.start_frame)
        ttk.Label(self.mask_options, text="Frame").grid(row=0, column=0)
        self.mask_frame_scale = tk.Scale(
            self.mask_options,
            from_=self.start_frame,
            to=self.end_frame,
            variable=self.mask_frame,
            resolution=1,
            orient=tk.HORIZONTAL,
        )
        self.mask_frame_scale.grid(row=0, column=1)
        handle_scale_release(self.mask_frame_scale, self.handle_mask_frame_change)

        self.display_mode = tk.StringVar()
        self.display_mode.set(DISPLAY_MODE_MASK)
        ttk.Label(self.mask_options, text="Display mode").grid(row=10, column=0)
        ttk.Radiobutton(
            self.mask_options,
            text=DISPLAY_MODE_MASK,
            value=DISPLAY_MODE_MASK,
            variable=self.display_mode,
            command=self.handle_display_change,
        ).grid(row=10, column=1, sticky="w")
        ttk.Radiobutton(
            self.mask_options,
            text=DISPLAY_MODE_PREVIEW,
            value=DISPLAY_MODE_PREVIEW,
            variable=self.display_mode,
            command=self.handle_display_change,
        ).grid(row=11, column=1, sticky="w")
        ttk.Radiobutton(
            self.mask_options,
            text=DISPLAY_MODE_ORIGINAL,
            value=DISPLAY_MODE_ORIGINAL,
            variable=self.display_mode,
            command=self.handle_display_change,
        ).grid(row=12, column=1, sticky="w")

        ttk.Label(self.mask_options, text="Display zoom").grid(
            row=20, column=0, columnspan=2, **self.section_padding
        )
        self.zoom_factor = tk.IntVar()
        self.zoom_factor.set(100)
        ttk.Label(self.mask_options, text="Zoom").grid(row=21, column=0)
        tk.Scale(
            self.mask_options,
            from_=1,
            to=500,
            variable=self.zoom_factor,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.render,
        ).grid(row=21, column=1)
        self.zoom_center_x = tk.IntVar()
        self.zoom_center_x.set(self.video_width // 2)
        ttk.Label(self.mask_options, text="Center x").grid(row=22, column=0)
        tk.Scale(
            self.mask_options,
            from_=0,
            to=self.video_width,
            variable=self.zoom_center_x,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.render,
        ).grid(row=22, column=1)
        self.zoom_center_y = tk.IntVar()
        self.zoom_center_y.set(self.video_height // 2)
        ttk.Label(self.mask_options, text="Center y").grid(row=23, column=0)
        tk.Scale(
            self.mask_options,
            from_=0,
            to=self.video_height,
            variable=self.zoom_center_y,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.render,
        ).grid(row=23, column=1)

        ttk.Label(self.mask_options, text="Hue / Saturation / Value").grid(
            row=100, column=0, columnspan=2, **self.section_padding
        )
        ttk.Button(
            self.mask_options, text="Color chooser", command=self.handle_colorchooser
        ).grid(row=101, column=0, columnspan=2)
        # OpenCV hue goes from 0 to 179
        hue_min, hue_max = 0, 179
        self.hue_min = tk.IntVar()
        self.hue_min.set(hue_min)
        ttk.Label(self.mask_options, text="Hue Min").grid(row=110, column=0)
        tk.Scale(
            self.mask_options,
            from_=0,
            to=179,
            variable=self.hue_min,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=110, column=1)
        self.hue_max = tk.IntVar()
        self.hue_max.set(hue_max)
        ttk.Label(self.mask_options, text="Hue Max").grid(row=111, column=0)
        tk.Scale(
            self.mask_options,
            from_=0,
            to=179,
            variable=self.hue_max,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=111, column=1)

        # Saturation
        sat_min, sat_max = 0, 255
        self.sat_min = tk.IntVar()
        self.sat_min.set(sat_min)
        ttk.Label(self.mask_options, text="Sat Min").grid(row=112, column=0)
        tk.Scale(
            self.mask_options,
            from_=0,
            to=255,
            variable=self.sat_min,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=112, column=1)
        self.sat_max = tk.IntVar()
        self.sat_max.set(sat_max)
        ttk.Label(self.mask_options, text="Sat Max").grid(row=113, column=0)
        tk.Scale(
            self.mask_options,
            from_=0,
            to=255,
            variable=self.sat_max,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=113, column=1)

        # Value
        val_min, val_max = 0, 255
        self.val_min = tk.IntVar()
        self.val_min.set(val_min)
        ttk.Label(self.mask_options, text="Val Min").grid(row=114, column=0)
        tk.Scale(
            self.mask_options,
            from_=0,
            to=255,
            variable=self.val_min,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=114, column=1)
        self.val_max = tk.IntVar()
        self.val_max.set(val_max)
        ttk.Label(self.mask_options, text="Val Max").grid(row=115, column=0)
        tk.Scale(
            self.mask_options,
            from_=0,
            to=255,
            variable=self.val_max,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=115, column=1)

        ttk.Label(self.mask_options, text="Crop").grid(
            row=200, column=0, columnspan=2, **self.section_padding
        )
        self.crop_left = tk.IntVar()
        self.crop_left.set(0)
        ttk.Label(self.mask_options, text="Left").grid(row=210, column=0)
        tk.Scale(
            self.mask_options,
            from_=0,
            to=self.video_width,
            variable=self.crop_left,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=210, column=1)
        self.crop_top = tk.IntVar()
        self.crop_top.set(0)
        ttk.Label(self.mask_options, text="Top").grid(row=211, column=0)
        tk.Scale(
            self.mask_options,
            from_=0,
            to=self.video_height,
            variable=self.crop_top,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=211, column=1)
        self.crop_right = tk.IntVar()
        self.crop_right.set(self.video_width)
        ttk.Label(self.mask_options, text="Right").grid(row=212, column=0)
        tk.Scale(
            self.mask_options,
            from_=0,
            to=self.video_width,
            variable=self.crop_right,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=212, column=1)
        self.crop_bottom = tk.IntVar()
        self.crop_bottom.set(self.video_height)
        ttk.Label(self.mask_options, text="Bottom").grid(row=213, column=0)
        tk.Scale(
            self.mask_options,
            from_=0,
            to=self.video_height,
            variable=self.crop_bottom,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=213, column=1)

        ttk.Label(self.mask_options, text="Other alteration").grid(
            row=300, column=0, columnspan=2, **self.section_padding
        )
        self.grow = tk.IntVar()
        self.grow.set(0)
        ttk.Label(self.mask_options, text="Grow").grid(row=301, column=0)
        tk.Scale(
            self.mask_options,
            from_=0,
            to=20,
            variable=self.grow,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=301, column=1)

        self.draw_mode = tk.StringVar()
        self.draw_mode.set(DRAW_MODE_NONE)
        ttk.Label(self.mask_options, text="Draw mode").grid(row=320, column=0)
        ttk.Radiobutton(
            self.mask_options,
            text=DRAW_MODE_NONE,
            value=DRAW_MODE_NONE,
            variable=self.draw_mode,
            command=self.handle_draw_mode,
        ).grid(row=320, column=1, sticky="w")
        ttk.Radiobutton(
            self.mask_options,
            text=DRAW_MODE_INCLUDE,
            value=DRAW_MODE_INCLUDE,
            variable=self.draw_mode,
            command=self.handle_draw_mode,
        ).grid(row=321, column=1, sticky="w")
        ttk.Radiobutton(
            self.mask_options,
            text=DRAW_MODE_EXCLUDE,
            value=DRAW_MODE_EXCLUDE,
            variable=self.draw_mode,
            command=self.handle_draw_mode,
        ).grid(row=322, column=1, sticky="w")
        ttk.Radiobutton(
            self.mask_options,
            text=DRAW_MODE_RESET,
            value=DRAW_MODE_RESET,
            variable=self.draw_mode,
            command=self.handle_draw_mode,
        ).grid(row=323, column=1, sticky="w")
        self.draw_size = tk.IntVar()
        self.draw_size.set(1)
        ttk.Label(self.mask_options, text="Draw size").grid(row=324, column=0)
        tk.Scale(
            self.mask_options,
            from_=1,
            to=50,
            variable=self.draw_size,
            resolution=1,
            orient=tk.HORIZONTAL,
        ).grid(row=324, column=1)
        self.draw_prev = None

        self.save_mask_button = ttk.Button(
            self.mask_options, text="Save mask", command=self.save_mask
        )
        self.save_mask_button.grid(
            row=1000, column=0, columnspan=2, **self.section_padding
        )

        # Make all mask tab widgets handle mousewheel events.
        self.mask_canvas.bind("<MouseWheel>", self.handle_mask_tab_mousewheel)
        self.mask_options.bind("<MouseWheel>", self.handle_mask_tab_mousewheel)
        for child in self.mask_options.children.values():
            child.bind("<MouseWheel>", self.handle_mask_tab_mousewheel)

    def build_render_tab(self):
        self.render_tab.columnconfigure(0, weight=1)
        self.render_tab.columnconfigure(1, weight=4)

        self.render_start_frame = tk.IntVar()
        self.render_start_frame.set(self.start_frame)
        ttk.Label(self.render_tab, text="Start frame").grid(row=0, column=0)
        self.render_start_frame_scale = tk.Scale(
            self.render_tab,
            from_=self.start_frame,
            to=self.end_frame,
            variable=self.render_start_frame,
            resolution=1,
            orient=tk.HORIZONTAL,
        )
        self.render_start_frame_scale.grid(row=0, column=1)
        handle_scale_release(
            self.render_start_frame_scale, self.handle_render_start_frame_change
        )

        self.render_end_frame = tk.IntVar()
        self.render_end_frame.set(self.end_frame)
        ttk.Label(self.render_tab, text="End frame").grid(row=1, column=0)
        self.render_end_frame_scale = tk.Scale(
            self.render_tab,
            from_=self.start_frame,
            to=self.end_frame,
            variable=self.render_end_frame,
            resolution=1,
            orient=tk.HORIZONTAL,
        )
        self.render_end_frame_scale.grid(row=1, column=1)
        handle_scale_release(
            self.render_end_frame_scale, self.handle_render_end_frame_change
        )

        self.save_render_button = ttk.Button(
            self.render_tab, text="Render", command=self.save_render
        )
        self.save_render_button.grid(
            row=1000, column=0, columnspan=2, **self.section_padding
        )

        # Don't render initially.
        self.render_progresslabel = ttk.Label(self.render_tab)
        self.render_progressbar = ttk.Progressbar(
            self.render_tab,
            orient="horizontal",
            mode="determinate",
        )

    def build_video_display(self):
        # Set up video display
        self.video_frame = ttk.Frame(self.frame, style="Video.TFrame")
        self.video_frame.pack(side="right", fill=None, expand=True)
        self.display = ttk.Label(self.video_frame)
        self.display.pack(fill="both", expand=True)
        self.display.bind("<Motion>", self.handle_display_motion)
        self.display.bind("<Button-1>", self.handle_display_drag)
        self.display.bind("<B1-Motion>", self.handle_display_drag)
        self.display.bind("<ButtonRelease-1>", self.handle_display_drag)

    def mainloop(self):
        self.root.mainloop()

    def handle_mask_tab_mousewheel(self, event):
        delta = -1 * event.delta
        if sys.platform != "darwin":
            delta = delta / 120
        self.mask_canvas.yview_scroll(int(delta), "units")

    def handle_draw_mode(self):
        draw_mode = self.draw_mode.get()
        if draw_mode == DRAW_MODE_NONE:
            self.display.config(cursor="")
        else:
            self.display.config(cursor="none")

    def _get_img_coords(self, zoomed_coords):
        zoomed_x, zoomed_y = zoomed_coords
        zoom_factor = self.zoom_factor.get() / 100
        crop_x, crop_y, _, _ = get_zoom_crop(
            zoom_factor,
            self.zoom_center_x.get(),
            self.zoom_center_y.get(),
            self.video_width,
            self.video_height,
            self.display_width,
            self.display_height,
        )
        # For the target pixel, compute the pixel in the original image.
        # crop_x and crop_y are the "origin" coordinates for the box in the
        # original image, so if we divide the scaled coordinates
        # by the zoom factor and add that to the "origin" coordinates,
        # we should get the original coordinates.
        img_x = int(zoomed_x // zoom_factor) + crop_x
        img_y = int(zoomed_y // zoom_factor) + crop_y
        return img_x, img_y

    def handle_display_motion(self, event):
        draw_mode = self.draw_mode.get()
        if draw_mode == DRAW_MODE_NONE:
            return

        img = self._display.copy()
        color = [200, 200, 200]
        draw_size = self.draw_size.get()
        img_x, img_y = self._get_img_coords((event.x, event.y))
        cv2.circle(img, (img_x, img_y), draw_size // 2, color=color, thickness=1)
        self.render(img=img)

    def handle_display_drag(self, event):
        draw_mode = self.draw_mode.get()
        if draw_mode == DRAW_MODE_NONE:
            return

        if event.type.name == "ButtonRelease":
            self.draw_prev = None
            return

        draw_size = self.draw_size.get()
        pt = self._get_img_coords((event.x, event.y))
        draw_prev = self.draw_prev or pt

        if draw_mode == DRAW_MODE_EXCLUDE:
            color = 0
        elif draw_mode == DRAW_MODE_RESET:
            color = 127
        else:
            # DRAW_MODE_INCLUDE
            color = 255

        cv2.line(self.draw_mask, draw_prev, pt, color, draw_size)
        self.draw_prev = pt

        self.handle_mask_change()

    def handle_display_configure(self, event):
        if event.widget == self.display and (
            self.display_width != event.width or self.display_height != event.height
        ):
            self.display_width = event.width
            self.display_height = event.height
            self.handle_display_change()

    def handle_colorchooser(self):
        # askcolor returns ((r, g, b), hex)
        color, _ = colorchooser.askcolor()
        if color is not None:
            pixel = np.array([[color]], np.uint8)
            pixel_hsv = cv2.cvtColor(pixel, cv2.COLOR_RGB2HSV)

            hue_min, sat_min, val_min = cv2.subtract(pixel_hsv, COLORCHOOSER_FUZZ)[0][0]
            hue_max, sat_max, val_max = cv2.add(pixel_hsv, COLORCHOOSER_FUZZ)[0][0]
            self.hue_min.set(hue_min)
            self.hue_max.set(hue_max)
            self.sat_min.set(sat_min)
            self.sat_max.set(sat_max)
            self.val_min.set(val_min)
            self.val_max.set(val_max)
            self.handle_mask_change()

    def handle_tab_change(self, val=None):
        if self.tabs.tab(self.tabs.select(), option="text") == "Mask":
            self.handle_mask_frame_change()
        else:
            self.handle_render_start_frame_change()
        self.render_progresslabel.grid_forget()
        self.render_progressbar.grid_forget()

    def handle_mask_frame_change(self, val=None):
        self.selected_mask_frame = get_frame(self.cap, self.mask_frame.get())
        self.handle_mask_change()

    def handle_render_start_frame_change(self, val=None):
        self.last_render_frame_changed = "start"
        self._cache_display(
            DISPLAY_MODE_ORIGINAL, get_frame(self.cap, self.render_start_frame.get())
        )
        self.render_progresslabel.grid_forget()
        self.render_progressbar.grid_forget()
        self.render()

    def handle_render_end_frame_change(self, val=None):
        self.last_render_frame_changed = "end"
        self._cache_display(
            DISPLAY_MODE_ORIGINAL, get_frame(self.cap, self.render_end_frame.get())
        )
        self.render_progresslabel.grid_forget()
        self.render_progressbar.grid_forget()
        self.render()

    def handle_mask_change(self, val=None):
        self._cache_mask()
        self._cache_display(self.display_mode.get(), self.selected_mask_frame)
        self.render()

    def handle_display_change(self, val=None):
        if self.tabs.tab(self.tabs.select(), option="text") == "Mask":
            self._cache_display(self.display_mode.get(), self.selected_mask_frame)
        elif self.last_render_frame_changed == "start":
            self.handle_render_start_frame_change()
        else:
            self.handle_render_end_frame_change()
        self.render()

    def _cache_mask(self):
        self._mask = render_mask(
            image=self.selected_mask_frame,
            hue_min=self.hue_min.get(),
            hue_max=self.hue_max.get(),
            sat_min=self.sat_min.get(),
            sat_max=self.sat_max.get(),
            val_min=self.val_min.get(),
            val_max=self.val_max.get(),
            grow=self.grow.get(),
            crop_left=self.crop_left.get(),
            crop_top=self.crop_top.get(),
            crop_right=self.crop_right.get(),
            crop_bottom=self.crop_bottom.get(),
            input_mask=self.input_mask,
            draw_mask=self.draw_mask,
        )

    def _cache_display(self, display_mode: str, frame: np.array):
        # Render the displayed image
        if display_mode == DISPLAY_MODE_ORIGINAL:
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        elif display_mode == DISPLAY_MODE_MASK:
            img = cv2.bitwise_and(frame, frame, mask=self._mask)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
        else:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = cv2.inpaint(
                frame_rgb, self._mask, self.inpaint_radius, cv2.INPAINT_TELEA
            )
            img = cv2.cvtColor(img, cv2.COLOR_RGB2RGBA)

        self._display = img

    def render(self, val=None, img=None):
        if img is None:
            img = self._display

        # Crop to the specified center, then zoom
        zoom_factor = self.zoom_factor.get() / 100
        crop_x, crop_y, zoom_width, zoom_height = get_zoom_crop(
            zoom_factor,
            self.zoom_center_x.get(),
            self.zoom_center_y.get(),
            self.video_width,
            self.video_height,
            self.display_width,
            self.display_height,
        )
        img = img[crop_y : crop_y + zoom_height, crop_x : crop_x + zoom_width]
        img = cv2.resize(
            img,
            None,
            fx=zoom_factor,
            fy=zoom_factor,
            interpolation=cv2.INTER_NEAREST,
        )

        imgtk = ImageTk.PhotoImage(image=Image.fromarray(img))

        # Prevent garbage collection
        self.display.imgtk = imgtk
        self.display.configure(image=imgtk)

    def save_mask(self):
        out_file = filedialog.asksaveasfilename(
            title="Save mask as",
        )
        cv2.imwrite(str(out_file), self._mask)

    def save_render(self):
        out_file = filedialog.asksaveasfilename(
            title="Render as",
        )
        if not out_file:
            return

        start_frame = self.render_start_frame.get()
        end_frame = self.render_end_frame.get()
        frame_count = end_frame - start_frame + 1

        # Steps: convert each frame to an image, clean each frame, and join them into the output file.
        step_count = (frame_count * 2) + 1

        self.render_progresslabel.config(text="Splitting frames...")
        print("Splitting frames...")
        self.render_progressbar.config(
            value=0,
            maximum=step_count,
            takefocus=True,
        )

        self.render_progresslabel.grid(
            row=2000, column=0, columnspan=2, **self.section_padding
        )
        self.render_progressbar.grid(row=2001, column=0, columnspan=2)
        self.root.update()

        with tempfile.TemporaryDirectory() as frames_dir:
            with tempfile.TemporaryDirectory() as cleaned_frames_dir:
                split_frames(
                    pathlib.Path(self.video_path),
                    pathlib.Path(frames_dir),
                    start=f"{start_frame / self.framerate}s",
                    end=f"{end_frame / self.framerate}s",
                )

                self.render_progressbar.step(frame_count)
                self.root.update()

                for _, cleaned_frame_path in clean_frames(
                    self._mask,
                    pathlib.Path(frames_dir),
                    pathlib.Path(cleaned_frames_dir),
                    self.inpaint_radius,
                ):
                    self.render_progresslabel.config(
                        text=f"Cleaning frames... {cleaned_frame_path.name}"
                    )
                    print(f"Cleaning frames... {cleaned_frame_path.name}")
                    self.render_progressbar.step()
                    self.root.update()

                self.render_progresslabel.config(text=f"Muxing to {out_file}")
                print(f"Muxing to {out_file}")
                self.render_progressbar.step()
                self.root.update()

                join_frames(
                    pathlib.Path(cleaned_frames_dir),
                    pathlib.Path(out_file),
                    self.framerate,
                    overwrite_output=True,
                )

        self.render_progresslabel.config(text=f"Done rendering {out_file}")
        print(f"Done rendering {out_file}")
        self.render_progressbar.config(takefocus=False)
        self.root.update()
