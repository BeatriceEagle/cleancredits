try:
    import tkinter as tk
    from tkinter import colorchooser, filedialog, ttk
except ModuleNotFoundError as exc:
    tk = None
    colorchooser = None
    filedialog = None
    ttk = None

import cv2
import numpy as np

from .slider import Slider
from .video_display import (
    DISPLAY_MODE_DRAW,
    DISPLAY_MODE_MASK,
    DISPLAY_MODE_ORIGINAL,
    DISPLAY_MODE_PREVIEW,
    DRAW_MODE_EXCLUDE,
    DRAW_MODE_INCLUDE,
    DRAW_MODE_RESET,
)


class MaskOptions(object):
    COLORCHOOSER_FUZZ = 10
    # OpenCV hue goes from 0 to 179
    HUE_MAX = 179
    SAT_MAX = 255
    VAL_MAX = 255

    section_padding = {"pady": (20, 0)}

    def __init__(
        self,
        parent,
        video_width,
        video_height,
        frame_count,
        zoom_factor_fit,
        video_display,
    ):
        self.parent = parent
        self.video_width = video_width
        self.video_height = video_height
        self.frame_count = frame_count
        self.video_display = video_display

        self.frame = tk.IntVar(value=0)
        self.display_mode = tk.StringVar(value=DISPLAY_MODE_MASK)
        self.zoom_factor = tk.DoubleVar(
            value=zoom_factor_fit,
        )
        self.zoom_center_x = tk.IntVar(value=video_width // 2)
        self.zoom_center_y = tk.IntVar(value=video_height // 2)
        self.hue_min = tk.IntVar(value=0)
        self.hue_max = tk.IntVar(value=self.HUE_MAX)
        self.sat_min = tk.IntVar(value=0)
        self.sat_max = tk.IntVar(value=self.SAT_MAX)
        self.val_min = tk.IntVar(value=0)
        self.val_max = tk.IntVar(value=self.VAL_MAX)
        self.crop_left = tk.IntVar(value=0)
        self.crop_top = tk.IntVar(value=0)
        self.crop_right = tk.IntVar(value=video_width)
        self.crop_bottom = tk.IntVar(value=video_height)
        self.grow = tk.IntVar(value=0)
        self.draw_mode_enable = tk.BooleanVar(value=False)
        self.draw_mode = tk.StringVar(value=DRAW_MODE_INCLUDE)
        self.draw_size = tk.IntVar(value=20)
        self.inpaint_radius = tk.IntVar(value=3)

    def build(self):
        self.scrollbar = ttk.Scrollbar(self.parent, orient=tk.VERTICAL)
        self.canvas = tk.Canvas(
            self.parent, width=300, height=480, yscrollcommand=self.scrollbar.set
        )
        self.scrollbar["command"] = self.canvas.yview

        self.options_container = ttk.Frame(self.canvas)

        self.frame_slider = Slider(
            self.options_container,
            "Frame",
            from_=0,
            to=self.frame_count - 1,
            variable=self.frame,
            command=self.handle_options_change,
        )

        self.display_mode_label = ttk.Label(self.options_container, text="Display mode")
        self.display_mode_radio_mask = ttk.Radiobutton(
            self.options_container,
            text=DISPLAY_MODE_MASK,
            value=DISPLAY_MODE_MASK,
            variable=self.display_mode,
            command=self.handle_options_change,
        )
        self.display_mode_radio_preview = ttk.Radiobutton(
            self.options_container,
            text=DISPLAY_MODE_PREVIEW,
            value=DISPLAY_MODE_PREVIEW,
            variable=self.display_mode,
            command=self.handle_options_change,
        )
        self.display_mode_radio_draw = ttk.Radiobutton(
            self.options_container,
            text=DISPLAY_MODE_DRAW,
            value=DISPLAY_MODE_DRAW,
            variable=self.display_mode,
            command=self.handle_options_change,
        )
        self.display_mode_radio_original = ttk.Radiobutton(
            self.options_container,
            text=DISPLAY_MODE_ORIGINAL,
            value=DISPLAY_MODE_ORIGINAL,
            variable=self.display_mode,
            command=self.handle_options_change,
        )

        self.display_zoom_label = ttk.Label(self.options_container, text="Display zoom")
        self.zoom_slider = Slider(
            self.options_container,
            "Zoom",
            from_=1,
            to=500,
            variable=self.zoom_factor,
            command=self.handle_options_change,
        )
        self.zoom_center_x_slider = Slider(
            self.options_container,
            "Center x",
            from_=0,
            to=self.video_width,
            variable=self.zoom_center_x,
            command=self.handle_options_change,
        )
        self.zoom_center_y_slider = Slider(
            self.options_container,
            "Center y",
            from_=0,
            to=self.video_height,
            variable=self.zoom_center_y,
            command=self.handle_options_change,
        )

        self.hsv_label = ttk.Label(
            self.options_container, text="Hue / Saturation / Value"
        )
        self.colorchooser_button = ttk.Button(
            self.options_container,
            text="Color chooser",
            command=self.handle_colorchooser,
        )
        self.hue_min_slider = Slider(
            self.options_container,
            "Hue Min",
            from_=0,
            to=self.HUE_MAX,
            variable=self.hue_min,
            command=self.handle_options_change,
        )
        self.hue_max_slider = Slider(
            self.options_container,
            "Hue Max",
            from_=0,
            to=self.HUE_MAX,
            variable=self.hue_max,
            command=self.handle_options_change,
        )
        self.sat_min_slider = Slider(
            self.options_container,
            "Sat Min",
            from_=0,
            to=self.SAT_MAX,
            variable=self.sat_min,
            command=self.handle_options_change,
        )
        self.sat_max_slider = Slider(
            self.options_container,
            "Sat Max",
            from_=0,
            to=self.SAT_MAX,
            variable=self.sat_max,
            command=self.handle_options_change,
        )
        self.val_min_slider = Slider(
            self.options_container,
            "Val Min",
            from_=0,
            to=self.VAL_MAX,
            variable=self.val_min,
            command=self.handle_options_change,
        )
        self.val_max_slider = Slider(
            self.options_container,
            "Val Max",
            from_=0,
            to=self.VAL_MAX,
            variable=self.val_max,
            command=self.handle_options_change,
        )

        self.crop_label = ttk.Label(self.options_container, text="Crop")
        self.crop_left_slider = Slider(
            self.options_container,
            "Left",
            from_=0,
            to=self.video_width,
            variable=self.crop_left,
            command=self.handle_options_change,
        )
        self.crop_top_slider = Slider(
            self.options_container,
            "Top",
            from_=0,
            to=self.video_height,
            variable=self.crop_top,
            command=self.handle_options_change,
        )
        self.crop_right_slider = Slider(
            self.options_container,
            "Right",
            from_=0,
            to=self.video_width,
            variable=self.crop_right,
            command=self.handle_options_change,
        )
        self.crop_bottom_slider = Slider(
            self.options_container,
            "Bottom",
            from_=0,
            to=self.video_height,
            variable=self.crop_bottom,
            command=self.handle_options_change,
        )

        self.other_alteration_label = ttk.Label(
            self.options_container, text="Other alteration"
        )
        self.grow_slider = Slider(
            self.options_container,
            "Grow",
            from_=0,
            to=20,
            variable=self.grow,
            command=self.handle_options_change,
        )

        self.draw_mode_enable_checkbox = ttk.Checkbutton(
            self.options_container,
            text="Draw/reset overrides",
            variable=self.draw_mode_enable,
            command=self.handle_draw_options_change,
        )
        self.draw_mode_label = ttk.Label(self.options_container, text="Override mode")
        self.draw_mode_reset_all_button = ttk.Button(
            self.options_container,
            text="Clear all",
            command=lambda: self.video_display.clear_overrides(),
        )
        self.draw_mode_radio_include = ttk.Radiobutton(
            self.options_container,
            text=DRAW_MODE_INCLUDE,
            value=DRAW_MODE_INCLUDE,
            variable=self.draw_mode,
            command=self.handle_draw_options_change,
        )
        self.draw_mode_radio_exclude = ttk.Radiobutton(
            self.options_container,
            text=DRAW_MODE_EXCLUDE,
            value=DRAW_MODE_EXCLUDE,
            variable=self.draw_mode,
            command=self.handle_draw_options_change,
        )
        self.draw_mode_radio_reset = ttk.Radiobutton(
            self.options_container,
            text=DRAW_MODE_RESET,
            value=DRAW_MODE_RESET,
            variable=self.draw_mode,
            command=self.handle_draw_options_change,
        )
        self.draw_size_slider = Slider(
            self.options_container,
            "Draw size",
            from_=1,
            to=200,
            variable=self.draw_size,
            command=self.handle_draw_options_change,
        )
        self.inpaint_radius_slider = Slider(
            self.options_container,
            "Inpaint radius",
            from_=0,
            to=10,
            variable=self.inpaint_radius,
            command=self.handle_options_change,
        )

        self.save_mask_button = ttk.Button(
            self.options_container, text="Save mask", command=self.save_mask
        )

        self.canvas.grid(column=0, row=0, sticky="nsew")
        self.canvas.grid_propagate(0)
        self.scrollbar.grid(column=1, row=0, sticky="ns")
        # options_container has to be positioned with create_window instead of grid
        # so that it will scroll properly
        self.canvas.create_window(
            0, 0, window=self.options_container, anchor=tk.NW, width=300
        )
        self.frame_slider.grid(row=0, column=0)

        self.display_mode_label.grid(row=10, column=0)
        self.display_mode_radio_mask.grid(row=10, column=1, sticky="w")
        self.display_mode_radio_preview.grid(row=11, column=1, sticky="w")
        self.display_mode_radio_draw.grid(row=12, column=1, sticky="w")
        self.display_mode_radio_original.grid(row=13, column=1, sticky="w")
        self.display_zoom_label.grid(
            row=20, column=0, columnspan=3, **self.section_padding
        )

        self.zoom_slider.grid(row=21, column=0)
        self.zoom_center_x_slider.grid(row=22, column=0)
        self.zoom_center_y_slider.grid(row=23, column=0)

        self.hsv_label.grid(row=100, column=0, columnspan=3, **self.section_padding)
        self.colorchooser_button.grid(row=101, column=0, columnspan=3)
        self.hue_min_slider.grid(row=110, column=0)
        self.hue_max_slider.grid(row=111, column=0)
        self.sat_min_slider.grid(row=112, column=0)
        self.sat_max_slider.grid(row=113, column=0)
        self.val_min_slider.grid(row=114, column=0)
        self.val_max_slider.grid(row=115, column=0)

        self.crop_label.grid(row=200, column=0, columnspan=3, **self.section_padding)
        self.crop_left_slider.grid(row=210, column=0)
        self.crop_top_slider.grid(row=211, column=0)
        self.crop_right_slider.grid(row=212, column=0)
        self.crop_bottom_slider.grid(row=213, column=0)

        self.other_alteration_label.grid(
            row=300, column=0, columnspan=3, **self.section_padding
        )
        self.grow_slider.grid(row=301, column=0)
        self.draw_mode_enable_checkbox.grid(row=320, column=1)
        self.draw_mode_label.grid(row=321, column=0)
        self.draw_mode_radio_include.grid(row=321, column=1, sticky="w")
        self.draw_mode_reset_all_button.grid(row=322, column=0)
        self.draw_mode_radio_exclude.grid(row=322, column=1, sticky="w")
        self.draw_mode_radio_reset.grid(row=323, column=1, sticky="w")
        self.draw_size_slider.grid(row=324, column=0)
        self.inpaint_radius_slider.grid(row=325, column=0)

        self.save_mask_button.grid(
            row=1000, column=0, columnspan=3, **self.section_padding
        )

        # Change canvas size when widgets are added to the inner frame
        self.options_container.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=(0, 0, 300, self.options_container.winfo_height())
            ),
        )

    def handle_selected(self):
        self.handle_draw_options_change()

    def handle_colorchooser(self):
        # askcolor returns ((r, g, b), hex)
        color, _ = colorchooser.askcolor()
        if color is not None:
            pixel = np.array([[color]], np.uint8)
            pixel_hsv = cv2.cvtColor(pixel, cv2.COLOR_RGB2HSV)

            hue_min, sat_min, val_min = cv2.subtract(pixel_hsv, self.COLORCHOOSER_FUZZ)[
                0
            ][0]
            hue_max, sat_max, val_max = cv2.add(pixel_hsv, self.COLORCHOOSER_FUZZ)[0][0]
            self.hue_min.set(hue_min)
            self.hue_max.set(hue_max)
            self.sat_min.set(sat_min)
            self.sat_max.set(sat_max)
            self.val_min.set(val_min)
            self.val_max.set(val_max)

    def handle_draw_options_change(self, e=None):
        if self.draw_mode_enable.get():
            self.draw_mode_reset_all_button.state(["!disabled"])
            self.draw_mode_radio_include.state(["!disabled"])
            self.draw_mode_radio_exclude.state(["!disabled"])
            self.draw_mode_radio_reset.state(["!disabled"])
            self.draw_size_slider.state(["!disabled"])
        else:
            self.draw_mode_reset_all_button.state(["disabled"])
            self.draw_mode_radio_include.state(["disabled"])
            self.draw_mode_radio_exclude.state(["disabled"])
            self.draw_mode_radio_reset.state(["disabled"])
            self.draw_size_slider.state(["disabled"])
        self.handle_options_change()

    def handle_options_change(self, e=None):
        self.video_display.set(
            {
                "frame_number": self.frame.get(),
                "hue_min": self.hue_min.get(),
                "hue_max": self.hue_max.get(),
                "sat_min": self.sat_min.get(),
                "sat_max": self.sat_max.get(),
                "val_min": self.val_min.get(),
                "val_max": self.val_max.get(),
                "grow": self.grow.get(),
                "crop_left": self.crop_left.get(),
                "crop_top": self.crop_top.get(),
                "crop_right": self.crop_right.get(),
                "crop_bottom": self.crop_bottom.get(),
                "display_mode": self.display_mode.get(),
                "zoom_factor": self.zoom_factor.get(),
                "zoom_center_x": self.zoom_center_x.get(),
                "zoom_center_y": self.zoom_center_y.get(),
                "draw_mode_enable": self.draw_mode_enable.get(),
                "draw_mode": self.draw_mode.get(),
                "draw_size": self.draw_size.get(),
                "inpaint_radius": self.inpaint_radius.get(),
            }
        )

    def save_mask(self):
        out_file = filedialog.asksaveasfilename(
            title="Save mask as",
        )
        if not out_file:
            return
        cv2.imwrite(str(out_file), self.video_display.get_mask())
