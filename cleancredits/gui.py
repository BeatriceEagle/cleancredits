import copy
import math
import pathlib
import tkinter as tk
from tkinter import colorchooser, ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

HSV_MODE_UNMASKED = "Unmasked"
HSV_MODE_MASKED = "Masked"
HSV_MODE_PREVIEW = "Preview"

SECTION_PADDING = {"pady": (50, 0)}

COLORCHOOSER_FUZZ = 10

DRAW_MODE_NONE = "None"
DRAW_MODE_EXCLUDE = "Exclude"
DRAW_MODE_INCLUDE = "Include"
DRAW_MODE_RESET = "Reset"


def handle_scale_release(scale, callback):
    scale.bind("<ButtonRelease-1>", callback)


class HSVMaskApp(ttk.Frame):
    def __init__(
        self,
        parent,
        cap,
        start_frame,
        end_frame,
        out_file: pathlib.Path,
        input_mask: pathlib.Path = None,
    ):
        super().__init__(parent)
        self.pack()

        self.style = ttk.Style(self)
        self.style.configure("Video.TFrame")
        self.style.configure("Options.TFrame")

        self.cap = cap
        self.video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.out_file = out_file
        self.input_mask = None
        if input_mask:
            self.input_mask = cv2.imread(str(input_mask))
            self.input_mask = cv2.cvtColor(self.input_mask, cv2.COLOR_BGR2GRAY)
        self.draw_mask = np.full((self.video_height, self.video_width), 127, np.uint8)

        # Set up video display
        self.video_frame = ttk.Frame(
            self, width=self.video_width, height=self.video_height, style="Video.TFrame"
        )
        self.video_frame.grid(row=0, column=0, sticky="nw")
        self.display = ttk.Label(self.video_frame)
        self.display.grid(row=0, column=0, sticky="nw")
        self.display.bind("<Motion>", self.handle_display_motion)
        self.display.bind("<Button-1>", self.handle_display_drag)
        self.display.bind("<B1-Motion>", self.handle_display_drag)
        self.display.bind("<ButtonRelease-1>", self.handle_display_drag)

        self.options_frame = ttk.Frame(self, style="Options.TFrame")
        self.options_frame.grid(row=0, column=1, sticky="n")

        self.options_frame.columnconfigure(0, weight=1)
        self.options_frame.columnconfigure(1, weight=4)

        self.selected_frame_num = tk.IntVar()
        self.selected_frame_num.set(start_frame)
        ttk.Label(self.options_frame, text="Frame").grid(row=0, column=0)
        self.current_frame_scale = tk.Scale(
            self.options_frame,
            from_=start_frame,
            to=end_frame,
            variable=self.selected_frame_num,
            resolution=1,
            orient=tk.HORIZONTAL,
        )
        self.current_frame_scale.grid(row=0, column=1)
        handle_scale_release(self.current_frame_scale, self.handle_frame_change)

        self.zoom_factor = tk.IntVar()
        self.zoom_factor.set(100)
        ttk.Label(self.options_frame, text="Zoom").grid(row=1, column=0)
        tk.Scale(
            self.options_frame,
            from_=100,
            to=500,
            variable=self.zoom_factor,
            resolution=25,
            orient=tk.HORIZONTAL,
            command=self.render,
        ).grid(row=1, column=1)
        self.zoom_center_x = tk.IntVar()
        self.zoom_center_x.set(self.video_width // 2)
        ttk.Label(self.options_frame, text="Zoom center x").grid(row=2, column=0)
        tk.Scale(
            self.options_frame,
            from_=0,
            to=self.video_width,
            variable=self.zoom_center_x,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.render,
        ).grid(row=2, column=1)
        self.zoom_center_y = tk.IntVar()
        self.zoom_center_y.set(self.video_height // 2)
        ttk.Label(self.options_frame, text="Zoom center y").grid(row=3, column=0)
        tk.Scale(
            self.options_frame,
            from_=0,
            to=self.video_height,
            variable=self.zoom_center_y,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.render,
        ).grid(row=3, column=1)

        self.display_mode = tk.StringVar()
        self.display_mode.set(HSV_MODE_MASKED)
        ttk.Label(self.options_frame, text="Display mode").grid(row=10, column=0)
        ttk.Radiobutton(
            self.options_frame,
            text=HSV_MODE_UNMASKED,
            value=HSV_MODE_UNMASKED,
            variable=self.display_mode,
            command=self.handle_display_change,
        ).grid(row=10, column=1, sticky="w")
        ttk.Radiobutton(
            self.options_frame,
            text=HSV_MODE_MASKED,
            value=HSV_MODE_MASKED,
            variable=self.display_mode,
            command=self.handle_display_change,
        ).grid(row=11, column=1, sticky="w")
        ttk.Radiobutton(
            self.options_frame,
            text=HSV_MODE_PREVIEW,
            value=HSV_MODE_PREVIEW,
            variable=self.display_mode,
            command=self.handle_display_change,
        ).grid(row=12, column=1, sticky="w")

        ttk.Label(self.options_frame, text="HSV Selection").grid(
            row=100, column=0, columnspan=2, **SECTION_PADDING
        )
        ttk.Button(
            self.options_frame, text="Color chooser", command=self.show_colorchooser
        ).grid(row=101, column=0, columnspan=2)
        # OpenCV hue goes from 0 to 179
        self.hue_min = tk.IntVar()
        self.hue_min.set(0)
        ttk.Label(self.options_frame, text="Hue Min").grid(row=110, column=0)
        tk.Scale(
            self.options_frame,
            from_=0,
            to=179,
            variable=self.hue_min,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=110, column=1)
        self.hue_max = tk.IntVar()
        self.hue_max.set(179)
        ttk.Label(self.options_frame, text="Hue Max").grid(row=111, column=0)
        tk.Scale(
            self.options_frame,
            from_=0,
            to=179,
            variable=self.hue_max,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=111, column=1)

        # Saturation
        self.sat_min = tk.IntVar()
        self.sat_min.set(0)
        ttk.Label(self.options_frame, text="Sat Min").grid(row=112, column=0)
        tk.Scale(
            self.options_frame,
            from_=0,
            to=255,
            variable=self.sat_min,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=112, column=1)
        self.sat_max = tk.IntVar()
        self.sat_max.set(255)
        ttk.Label(self.options_frame, text="Sat Max").grid(row=113, column=0)
        tk.Scale(
            self.options_frame,
            from_=0,
            to=255,
            variable=self.sat_max,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=113, column=1)

        # Value
        self.val_min = tk.IntVar()
        self.val_min.set(0)
        ttk.Label(self.options_frame, text="Val Min").grid(row=105, column=0)
        tk.Scale(
            self.options_frame,
            from_=0,
            to=255,
            variable=self.val_min,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=105, column=1)
        self.val_max = tk.IntVar()
        self.val_max.set(255)
        ttk.Label(self.options_frame, text="Val Max").grid(row=106, column=0)
        tk.Scale(
            self.options_frame,
            from_=0,
            to=255,
            variable=self.val_max,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=106, column=1)

        ttk.Label(self.options_frame, text="Mask alteration").grid(
            row=200, column=0, columnspan=2, **SECTION_PADDING
        )
        self.grow = tk.IntVar()
        self.grow.set(0)
        ttk.Label(self.options_frame, text="Grow").grid(row=201, column=0)
        tk.Scale(
            self.options_frame,
            from_=0,
            to=20,
            variable=self.grow,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=201, column=1)

        self.bbox_x1 = tk.IntVar()
        self.bbox_x1.set(0)
        ttk.Label(self.options_frame, text="Bounding Box X1").grid(row=210, column=0)
        tk.Scale(
            self.options_frame,
            from_=0,
            to=self.video_width,
            variable=self.bbox_x1,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=210, column=1)
        self.bbox_y1 = tk.IntVar()
        self.bbox_y1.set(0)
        ttk.Label(self.options_frame, text="Bounding Box Y1").grid(row=211, column=0)
        tk.Scale(
            self.options_frame,
            from_=0,
            to=self.video_height,
            variable=self.bbox_y1,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=211, column=1)
        self.bbox_x2 = tk.IntVar()
        self.bbox_x2.set(self.video_width)
        ttk.Label(self.options_frame, text="Bounding Box X2").grid(row=212, column=0)
        tk.Scale(
            self.options_frame,
            from_=0,
            to=self.video_width,
            variable=self.bbox_x2,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=212, column=1)
        self.bbox_y2 = tk.IntVar()
        self.bbox_y2.set(self.video_height)
        ttk.Label(self.options_frame, text="Bounding Box Y2").grid(row=213, column=0)
        tk.Scale(
            self.options_frame,
            from_=0,
            to=self.video_height,
            variable=self.bbox_y2,
            resolution=1,
            orient=tk.HORIZONTAL,
            command=self.handle_mask_change,
        ).grid(row=213, column=1)

        self.draw_mode = tk.StringVar()
        self.draw_mode.set(DRAW_MODE_NONE)
        ttk.Label(self.options_frame, text="Draw mode").grid(row=220, column=0)
        ttk.Radiobutton(
            self.options_frame,
            text=DRAW_MODE_NONE,
            value=DRAW_MODE_NONE,
            variable=self.draw_mode,
            command=self.handle_draw_mode,
        ).grid(row=220, column=1, sticky="w")
        ttk.Radiobutton(
            self.options_frame,
            text=DRAW_MODE_INCLUDE,
            value=DRAW_MODE_INCLUDE,
            variable=self.draw_mode,
            command=self.handle_draw_mode,
        ).grid(row=221, column=1, sticky="w")
        ttk.Radiobutton(
            self.options_frame,
            text=DRAW_MODE_EXCLUDE,
            value=DRAW_MODE_EXCLUDE,
            variable=self.draw_mode,
            command=self.handle_draw_mode,
        ).grid(row=222, column=1, sticky="w")
        ttk.Radiobutton(
            self.options_frame,
            text=DRAW_MODE_RESET,
            value=DRAW_MODE_RESET,
            variable=self.draw_mode,
            command=self.handle_draw_mode,
        ).grid(row=223, column=1, sticky="w")
        self.draw_size = tk.IntVar()
        self.draw_size.set(1)
        ttk.Label(self.options_frame, text="Draw size").grid(row=224, column=0)
        tk.Scale(
            self.options_frame,
            from_=1,
            to=50,
            variable=self.draw_size,
            resolution=1,
            orient=tk.HORIZONTAL,
        ).grid(row=224, column=1)
        self.draw_prev = None

        self.save_button = ttk.Button(
            self.options_frame, text="Save and quit", command=self.save_and_quit
        )
        self.save_button.grid(row=1000, column=0, columnspan=2, **SECTION_PADDING)

        # First render is basically a frame change.
        self.handle_frame_change()

    def handle_draw_mode(self):
        draw_mode = self.draw_mode.get()
        if draw_mode == DRAW_MODE_NONE:
            self.display.config(cursor="")
        else:
            self.display.config(cursor="none")

    def get_zoom_and_crop(self):
        zoom_factor = self.zoom_factor.get() / 100
        zoom_center_x = self.zoom_center_x.get()
        zoom_center_y = self.zoom_center_y.get()
        zoom_width = int(self.video_width // zoom_factor)
        zoom_height = int(self.video_height // zoom_factor)
        crop_x = np.clip(
            zoom_center_x - (zoom_width // 2), 0, self.video_width - zoom_width
        )
        crop_y = np.clip(
            zoom_center_y - (zoom_height // 2), 0, self.video_height - zoom_height
        )
        return zoom_factor, crop_x, crop_y, zoom_width, zoom_height

    def handle_display_motion(self, event):
        draw_mode = self.draw_mode.get()
        if draw_mode == DRAW_MODE_NONE:
            return

        img = self._display.copy()
        color = [200, 200, 200]
        draw_size = self.draw_size.get()
        zoom_factor, crop_x, crop_y, zoom_width, zoom_height = self.get_zoom_and_crop()
        img_x = int(event.x // zoom_factor) + crop_x
        img_y = int(event.y // zoom_factor) + crop_y
        # For the target pixel, compute the pixel in the original image.
        # crop_x and crop_y are the "origin" coordinates for the box in the
        # original image, so if we divide the scaled coordinates
        # by the zoom factor and add that to the "origin" coordinates,
        # we should get the original coordinates.
        cv2.circle(img, (img_x, img_y), draw_size // 2, color=color, thickness=1)
        self.render(img=img)

    def handle_display_drag(self, event):
        draw_mode = self.draw_mode.get()
        if draw_mode == DRAW_MODE_NONE:
            return

        if event.type.name == "ButtonPress":
            self.draw_prev = (event.x, event.y)
            return

        if event.type.name == "ButtonRelease":
            self.draw_prev = None
            return

        draw_size = self.draw_size.get()
        pt = (event.x, event.y)
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

        self._cache_mask()
        self._cache_display()
        self.render()

    def show_colorchooser(self):
        color = colorchooser.askcolor()
        if color is not None:
            pixel = np.array([[color[0]]], np.uint8)
            pixel_hsv = cv2.cvtColor(pixel, cv2.COLOR_RGB2HSV)
            hue, sat, val = pixel_hsv[0][0]
            self.hue_min.set(hue - COLORCHOOSER_FUZZ)
            self.hue_max.set(hue + COLORCHOOSER_FUZZ)
            self.sat_min.set(sat - COLORCHOOSER_FUZZ)
            self.sat_max.set(sat + COLORCHOOSER_FUZZ)
            self.val_min.set(val - COLORCHOOSER_FUZZ)
            self.val_max.set(val + COLORCHOOSER_FUZZ)
            self._cache_display()
            self.render()

    def _select_frame(self):
        selected_frame_num = self.selected_frame_num.get()
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, selected_frame_num)
        _, self.selected_frame = self.cap.read()
        if self.selected_frame is None:
            raise Exception(f"Invalid frame: {selected_frame_num}")

    def handle_frame_change(self, val=None):
        self._select_frame()
        self._cache_mask()
        self._cache_display()
        self.render()

    def handle_mask_change(self, val=None):
        self._cache_mask()
        self._cache_display()
        self.render()

    def handle_display_change(self, val=None):
        self._cache_display()
        self.render()

    def _cache_mask(self):
        hue_min = self.hue_min.get()
        hue_max = self.hue_max.get()
        sat_min = self.sat_min.get()
        sat_max = self.sat_max.get()
        val_min = self.val_min.get()
        val_max = self.val_max.get()

        grow = self.grow.get()
        bbox_x1 = self.bbox_x1.get()
        bbox_y1 = self.bbox_y1.get()
        bbox_x2 = self.bbox_x2.get()
        bbox_y2 = self.bbox_y2.get()

        # Set up np arrays for lower/upper bounds for mask range
        hsv_min = np.array([hue_min, sat_min, val_min])
        hsv_max = np.array([hue_max, sat_max, val_max])

        frame_hsv = cv2.cvtColor(self.selected_frame, cv2.COLOR_BGR2HSV)
        hsv_mask = cv2.inRange(frame_hsv, hsv_min, hsv_max)

        # Modify the hsv_mask
        if grow > 0:
            kernel = np.ones((grow, grow), np.uint8)
            hsv_mask = cv2.dilate(hsv_mask, kernel, iterations=1)

        bbox_mask = np.zeros(hsv_mask.shape, np.uint8)
        bbox_mask[bbox_y1:bbox_y2, bbox_x1:bbox_x2] = 255
        mask = cv2.bitwise_and(hsv_mask, hsv_mask, mask=bbox_mask)

        # Combine with base mask in bitwise_or
        if self.input_mask:
            mask = cv2.bitwise_or(mask, self.input_mask)

        # Combine with include/exclude masks
        _, include_mask = cv2.threshold(self.draw_mask, 128, 255, cv2.THRESH_BINARY)
        mask = cv2.bitwise_or(mask, include_mask)
        _, exclude_mask = cv2.threshold(self.draw_mask, 126, 255, cv2.THRESH_BINARY)
        mask = cv2.bitwise_and(mask, exclude_mask)

        self._mask = mask

    def _cache_display(self):
        display_mode = self.display_mode.get()
        # TODO: Make radius configurable
        radius = 3

        # Render the displayed image
        if display_mode == HSV_MODE_UNMASKED:
            img = cv2.cvtColor(self.selected_frame, cv2.COLOR_BGR2RGBA)
        elif display_mode == HSV_MODE_MASKED:
            img = cv2.bitwise_and(
                self.selected_frame, self.selected_frame, mask=self._mask
            )
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
        else:
            frame_rgb = cv2.cvtColor(self.selected_frame, cv2.COLOR_BGR2RGB)
            img = cv2.inpaint(frame_rgb, self._mask, radius, cv2.INPAINT_TELEA)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2RGBA)

        self._display = img

    def render(self, val=None, img=None):
        if img is None:
            img = self._display

        # Crop to the specified center, then zoom
        zoom_factor, crop_x, crop_y, zoom_width, zoom_height = self.get_zoom_and_crop()
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

    def save_and_quit(self):
        cv2.imwrite(str(self.out_file), self._mask)
        self.master.destroy()
