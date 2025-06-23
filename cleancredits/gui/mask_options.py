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

from ..helpers import MASK_MODE_EXCLUDE, MASK_MODE_INCLUDE, combine_masks
from .slider import Slider
from .video_display import (
    DISPLAY_MODE_DRAW,
    DISPLAY_MODE_MASK,
    DISPLAY_MODE_ORIGINAL,
    DISPLAY_MODE_PREVIEW,
    DRAW_MODE_EXCLUDE,
    DRAW_MODE_INCLUDE,
    DRAW_MODE_RESET,
    FRAME_SETTINGS,
    MASK_SETTINGS,
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
        self.zoom_factor_fit = zoom_factor_fit

        self._input_mask = None
        self.mask_frame_number = tk.IntVar()
        self.display_mode = tk.StringVar()
        self.zoom_factor = tk.DoubleVar()
        self.zoom_center_x = tk.IntVar()
        self.zoom_center_y = tk.IntVar()
        self.mask_mode = tk.StringVar()
        self.hue_min = tk.IntVar()
        self.hue_max = tk.IntVar()
        self.sat_min = tk.IntVar()
        self.sat_max = tk.IntVar()
        self.val_min = tk.IntVar()
        self.val_max = tk.IntVar()
        self.crop_left = tk.IntVar()
        self.crop_top = tk.IntVar()
        self.crop_right = tk.IntVar()
        self.crop_bottom = tk.IntVar()
        self.grow = tk.IntVar()
        self.draw_mode_enable = tk.BooleanVar()
        self.draw_mode = tk.StringVar()
        self.draw_size = tk.IntVar()
        self.inpaint_radius = tk.IntVar()

        self.set_options(self.get_default_options())

    def build(self):
        self.scrollbar = ttk.Scrollbar(self.parent, orient=tk.VERTICAL)
        self.canvas = tk.Canvas(
            self.parent, width=300, height=480, yscrollcommand=self.scrollbar.set
        )
        self.scrollbar["command"] = self.canvas.yview

        self.options_container = ttk.Frame(self.canvas)

        self.layer_selector = LayerSelector(
            self.options_container,
            "Layer",
            self,
        )

        self.frame_slider = Slider(
            self.options_container,
            "Frame",
            from_=0,
            to=self.frame_count - 1,
            variable=self.mask_frame_number,
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

        self.mask_mode_label = ttk.Label(self.options_container, text="Mask mode")
        self.mask_mode_radio_include = ttk.Radiobutton(
            self.options_container,
            text=MASK_MODE_INCLUDE,
            value=MASK_MODE_INCLUDE,
            variable=self.mask_mode,
        )
        self.mask_mode_radio_exclude = ttk.Radiobutton(
            self.options_container,
            text=MASK_MODE_EXCLUDE,
            value=MASK_MODE_EXCLUDE,
            variable=self.mask_mode,
        )
        # Use trace_add instead of command so that changes to this (even due to a new layer being added)
        # will trigger a re-render. This isn't necessary for non-mask options because they don't change
        # when a layer is added, and it's not necessary for other mask options because they already
        # have this behavior as a side effect of the slider implementation.
        self.mask_mode.trace_add("write", self.handle_options_change)
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

        self.canvas.grid(column=0, row=0, sticky="nsew")
        self.canvas.grid_propagate(0)
        self.scrollbar.grid(column=1, row=0, sticky="ns")
        # options_container has to be positioned with create_window instead of grid
        # so that it will scroll properly
        self.canvas.create_window(
            0, 0, window=self.options_container, anchor=tk.NW, width=300
        )
        self.layer_selector.grid(row=0, column=0, columnspan=3, sticky="ew")
        self.frame_slider.grid(row=5, column=0)

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
        self.mask_mode_label.grid(row=301, column=0)
        self.mask_mode_radio_include.grid(row=301, column=1, sticky="w")
        self.mask_mode_radio_exclude.grid(row=302, column=1, sticky="w")
        self.grow_slider.grid(row=310, column=0)
        self.draw_mode_enable_checkbox.grid(row=320, column=1)
        self.draw_mode_label.grid(row=321, column=0)
        self.draw_mode_radio_include.grid(row=321, column=1, sticky="w")
        self.draw_mode_reset_all_button.grid(row=322, column=0)
        self.draw_mode_radio_exclude.grid(row=322, column=1, sticky="w")
        self.draw_mode_radio_reset.grid(row=323, column=1, sticky="w")
        self.draw_size_slider.grid(row=324, column=0)
        self.inpaint_radius_slider.grid(row=325, column=0)

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

    def get_default_options(self):
        return {
            "mask_frame_number": 0,
            "input_mask": None,
            "mask_mode": MASK_MODE_INCLUDE,
            "hue_min": 0,
            "hue_max": self.HUE_MAX,
            "sat_min": 0,
            "sat_max": self.SAT_MAX,
            "val_min": 0,
            "val_max": self.VAL_MAX,
            "grow": 0,
            "crop_left": 0,
            "crop_top": 0,
            "crop_right": self.video_width,
            "crop_bottom": self.video_height,
            "display_mode": DISPLAY_MODE_MASK,
            "zoom_factor": self.zoom_factor_fit,
            "zoom_center_x": self.video_width // 2,
            "zoom_center_y": self.video_height // 2,
            "draw_mode_enable": False,
            "draw_mode": DRAW_MODE_INCLUDE,
            "draw_size": 20,
            "inpaint_radius": 3,
        }

    def get_options(self):
        return {
            "mask_frame_number": self.mask_frame_number.get(),
            "input_mask": self._input_mask,
            "mask_mode": self.mask_mode.get(),
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

    def set_options(self, options):
        if "input_mask" in options:
            self._input_mask = options.pop("input_mask")
        for k, v in options.items():
            variable = getattr(self, k)
            variable.set(v)

    def handle_options_change(self, *args):
        options = self.get_options()
        # Mirror mask frame number to also be displayed.
        options["display_frame_number"] = options["mask_frame_number"]
        self.video_display.set(options)


class LayerSelector(object):
    def __init__(self, parent, text, mask_options):
        self.parent = parent
        self.container = ttk.Frame(parent)

        self.mask_options = mask_options

        self.layers = [{}]

        self.selected_index = 0

        self.label = ttk.Label(self.container, text=text, anchor="center")
        self.select_button_frame = ttk.Frame(self.container)
        self.select_buttons = []
        self.add_button = ttk.Button(
            self.select_button_frame, text="+", command=self.handle_add
        )
        self.delete_frame = ttk.Frame(self.container)
        self.delete_button = ttk.Button(
            self.delete_frame, text="Delete current layer", command=self.handle_delete
        )

        self.container.grid_columnconfigure(0, weight=1)
        self.label.grid(row=0, column=0, sticky="ew")
        self.select_button_frame.grid(row=1, column=0, sticky="ew")
        self.delete_frame.grid(row=2, column=0, sticky="ew")
        self.delete_button.grid(row=0, column=1)
        self.delete_frame.grid_columnconfigure(0, weight=1)
        self.delete_frame.grid_columnconfigure(2, weight=1)

        self.build()

    def grid(self, *args, **kwargs):
        self.container.grid(*args, **kwargs)

    def build(self):
        layer_count = len(self.layers)
        if self.select_buttons:
            for button in self.select_buttons:
                button.destroy()
        self.select_buttons = []

        for i in range(layer_count):

            def handler(index):
                return lambda: self.handle_select(index)

            button = ttk.Button(
                self.select_button_frame,
                text=i + 1,
                command=handler(i),
            )
            self.select_buttons.append(button)
            button.grid(row=0, column=i + 1)
            if i == self.selected_index:
                button["default"] = "active"
            else:
                button["default"] = "normal"

        self.add_button.grid(row=0, column=layer_count + 1)

        # Center select buttons horizontally
        # First, clear weights (even if a button was deleted)
        for i in range(1, 8):
            self.select_button_frame.grid_columnconfigure(i, weight=0)
        self.select_button_frame.grid_columnconfigure(0, weight=1)
        self.select_button_frame.grid_columnconfigure(layer_count + 2, weight=1)

        if layer_count <= 1:
            self.delete_button.state(["disabled"])
        else:
            self.delete_button.state(["!disabled"])

        if layer_count >= 5:
            self.add_button.grid_forget()

    def save_layer(self, index, mask):
        options = self.mask_options.get_options()
        self.layers[index] = {k: options[k] for k in MASK_SETTINGS}
        self.layers[index]["mask"] = mask

    def add_layer(self):
        default_options = self.mask_options.get_default_options()
        new_layer = {k: default_options[k] for k in MASK_SETTINGS}
        # Keep the same frame we were already on - chances are the user wants to get a different aspect of it.
        new_layer["mask_frame_number"] = self.layers[self.selected_index][
            "mask_frame_number"
        ]
        self.layers.append(new_layer)

    def load_layer(self, index):
        # Build the input mask first
        input_mask = None
        for layer in self.layers[0:index]:
            input_mask = combine_masks(
                layer["mask_mode"],
                layer["mask"],
                input_mask,
            )
        self.layers[index]["input_mask"] = input_mask
        layer = self.layers[index]
        self.mask_options.set_options({k: layer[k] for k in MASK_SETTINGS})
        self.selected_index = index

    def handle_select(self, index):
        if index < 0 or index >= len(self.layers):
            print("Invalid index")
            return
        if self.selected_index == index:
            return

        self.save_layer(self.selected_index, self.mask_options.video_display.get_mask())
        self.load_layer(index)
        self.build()

    def handle_add(self):
        self.add_layer()
        self.handle_select(len(self.layers) - 1)

    def handle_delete(self):
        del self.layers[self.selected_index]
        self.load_layer(min(self.selected_index, len(self.layers) - 1))
        self.build()
