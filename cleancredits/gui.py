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

SECTION_PADDING = (50, 0)

COLORCHOOSER_FUZZ = 10


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
        video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.out_file = out_file
        self.input_mask = None
        if input_mask:
            self.input_mask = cv2.imread(str(input_mask), cv2.IMREAD_GRAYSCALE)

        # Set up video display
        self.video_frame = ttk.Frame(
            self, width=video_width, height=video_height, style="Video.TFrame"
        )
        self.video_frame.grid(row=0, column=0, sticky="nw")
        self.video_label = ttk.Label(self.video_frame)
        self.video_label.grid(row=0, column=0, sticky="nw")

        self.options_frame = ttk.Frame(self, style="Options.TFrame")
        self.options_frame.grid(row=0, column=1, sticky="n")

        self.options_frame.columnconfigure(0, weight=1)
        self.options_frame.columnconfigure(1, weight=4)

        self.current_frame = tk.IntVar()
        self.current_frame.set(start_frame)
        ttk.Label(self.options_frame, text="Frame").grid(row=0, column=0)
        self.current_frame_scale = tk.Scale(
            self.options_frame,
            from_=start_frame,
            to=end_frame,
            variable=self.current_frame,
            resolution=1,
            orient=tk.HORIZONTAL,
        )
        self.current_frame_scale.grid(row=0, column=1)
        self.bind_scale(self.current_frame_scale)

        self.display_mode = tk.StringVar()
        self.display_mode.set(HSV_MODE_MASKED)
        ttk.Label(self.options_frame, text="Display mode").grid(row=1, column=0)
        ttk.Radiobutton(
            self.options_frame,
            text=HSV_MODE_UNMASKED,
            value=HSV_MODE_UNMASKED,
            variable=self.display_mode,
            command=self.show_frame,
        ).grid(row=1, column=1, sticky="w")
        ttk.Radiobutton(
            self.options_frame,
            text=HSV_MODE_MASKED,
            value=HSV_MODE_MASKED,
            variable=self.display_mode,
            command=self.show_frame,
        ).grid(row=2, column=1, sticky="w")
        ttk.Radiobutton(
            self.options_frame,
            text=HSV_MODE_PREVIEW,
            value=HSV_MODE_PREVIEW,
            variable=self.display_mode,
            command=self.show_frame,
        ).grid(row=3, column=1, sticky="w")

        ttk.Label(self.options_frame, text="HSV Selection").grid(
            row=100, column=0, columnspan=2, pady=SECTION_PADDING
        )
        ttk.Button(
            self.options_frame, text="Color chooser", command=self.show_colorchooser
        ).grid(row=101, column=0, columnspan=2)
        # OpenCV hue goes from 0 to 179
        self.hue_min = tk.IntVar()
        self.hue_min.set(0)
        ttk.Label(self.options_frame, text="Hue Min").grid(row=110, column=0)
        self.hue_min_scale = tk.Scale(
            self.options_frame,
            from_=0,
            to=179,
            variable=self.hue_min,
            resolution=1,
            orient=tk.HORIZONTAL,
        )
        self.hue_min_scale.grid(row=110, column=1)
        self.bind_scale(self.hue_min_scale)
        self.hue_max = tk.IntVar()
        self.hue_max.set(179)
        ttk.Label(self.options_frame, text="Hue Max").grid(row=111, column=0)
        self.hue_max_scale = tk.Scale(
            self.options_frame,
            from_=0,
            to=179,
            variable=self.hue_max,
            resolution=1,
            orient=tk.HORIZONTAL,
        )
        self.hue_max_scale.grid(row=111, column=1)
        self.bind_scale(self.hue_max_scale)

        # Saturation
        self.sat_min = tk.IntVar()
        self.sat_min.set(0)
        ttk.Label(self.options_frame, text="Sat Min").grid(row=112, column=0)
        self.sat_min_scale = tk.Scale(
            self.options_frame,
            from_=0,
            to=255,
            variable=self.sat_min,
            resolution=1,
            orient=tk.HORIZONTAL,
        )
        self.sat_min_scale.grid(row=112, column=1)
        self.bind_scale(self.sat_min_scale)
        self.sat_max = tk.IntVar()
        self.sat_max.set(255)
        ttk.Label(self.options_frame, text="Sat Max").grid(row=113, column=0)
        self.sat_max_scale = tk.Scale(
            self.options_frame,
            from_=0,
            to=255,
            variable=self.sat_max,
            resolution=1,
            orient=tk.HORIZONTAL,
        )
        self.sat_max_scale.grid(row=113, column=1)
        self.bind_scale(self.sat_max_scale)

        # Value
        self.val_min = tk.IntVar()
        self.val_min.set(0)
        ttk.Label(self.options_frame, text="Val Min").grid(row=105, column=0)
        self.val_min_scale = tk.Scale(
            self.options_frame,
            from_=0,
            to=255,
            variable=self.val_min,
            resolution=1,
            orient=tk.HORIZONTAL,
        )
        self.val_min_scale.grid(row=105, column=1)
        self.bind_scale(self.val_min_scale)
        self.val_max = tk.IntVar()
        self.val_max.set(255)
        ttk.Label(self.options_frame, text="Val Max").grid(row=106, column=0)
        self.val_max_scale = tk.Scale(
            self.options_frame,
            from_=0,
            to=255,
            variable=self.val_max,
            resolution=1,
            orient=tk.HORIZONTAL,
        )
        self.val_max_scale.grid(row=106, column=1)
        self.bind_scale(self.val_max_scale)

        ttk.Label(self.options_frame, text="Mask alteration").grid(
            row=200, column=0, columnspan=2, pady=SECTION_PADDING
        )
        self.grow = tk.IntVar()
        self.grow.set(0)
        ttk.Label(self.options_frame, text="Grow").grid(row=201, column=0)
        self.grow_scale = tk.Scale(
            self.options_frame,
            from_=0,
            to=20,
            variable=self.grow,
            resolution=1,
            orient=tk.HORIZONTAL,
        )
        self.grow_scale.grid(row=201, column=1)
        self.bind_scale(self.grow_scale)

        self.bbox_x1 = tk.IntVar()
        self.bbox_x1.set(0)
        ttk.Label(self.options_frame, text="Bounding Box X1").grid(row=210, column=0)
        self.bbox_x1_scale = tk.Scale(
            self.options_frame,
            from_=0,
            to=video_width,
            variable=self.bbox_x1,
            resolution=1,
            orient=tk.HORIZONTAL,
        )
        self.bbox_x1_scale.grid(row=210, column=1)
        self.bind_scale(self.bbox_x1_scale)
        self.bbox_y1 = tk.IntVar()
        self.bbox_y1.set(0)
        ttk.Label(self.options_frame, text="Bounding Box Y1").grid(row=211, column=0)
        self.bbox_y1_scale = tk.Scale(
            self.options_frame,
            from_=0,
            to=video_height,
            variable=self.bbox_y1,
            resolution=1,
            orient=tk.HORIZONTAL,
        )
        self.bbox_y1_scale.grid(row=211, column=1)
        self.bind_scale(self.bbox_y1_scale)
        self.bbox_x2 = tk.IntVar()
        self.bbox_x2.set(video_width)
        ttk.Label(self.options_frame, text="Bounding Box X2").grid(row=212, column=0)
        self.bbox_x2_scale = tk.Scale(
            self.options_frame,
            from_=0,
            to=video_width,
            variable=self.bbox_x2,
            resolution=1,
            orient=tk.HORIZONTAL,
        )
        self.bbox_x2_scale.grid(row=212, column=1)
        self.bind_scale(self.bbox_x2_scale)
        self.bbox_y2 = tk.IntVar()
        self.bbox_y2.set(video_height)
        ttk.Label(self.options_frame, text="Bounding Box Y2").grid(row=213, column=0)
        self.bbox_y2_scale = tk.Scale(
            self.options_frame,
            from_=0,
            to=video_height,
            variable=self.bbox_y2,
            resolution=1,
            orient=tk.HORIZONTAL,
        )
        self.bbox_y2_scale.grid(row=213, column=1)
        self.bind_scale(self.bbox_y2_scale)

        self.save_button = ttk.Button(
            self.options_frame, text="Save and quit", command=self.save_and_quit
        )
        self.save_button.grid(row=1000, column=0, columnspan=2)

        self.show_frame()

    def bind_scale(self, scale):
        scale.bind("<ButtonRelease-1>", self.show_frame)

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
            self.show_frame()

    def _get_mask(self):
        current_frame = self.current_frame.get()
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

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        _, frame = self.cap.read()
        if frame is None:
            raise Exception(f"Invalid frame: {current_frame}")

        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hsv_mask = cv2.inRange(frame_hsv, hsv_min, hsv_max)

        # Modify the hsv_mask
        if grow > 0:
            kernel = np.ones((grow, grow), np.uint8)
            hsv_mask = cv2.dilate(hsv_mask, kernel, iterations=1)

        bbox_mask = np.zeros(hsv_mask.shape, np.uint8)
        bbox_mask[bbox_y1:bbox_y2, bbox_x1:bbox_x2] = 255
        hsv_mask = cv2.bitwise_and(hsv_mask, hsv_mask, mask=bbox_mask)

        # Combine with base mask in bitwise_or
        mask = cv2.bitwise_or(hsv_mask, self.input_mask)

        return frame, mask

    def show_frame(self, val=None):
        frame, mask = self._get_mask()
        display_mode = self.display_mode.get()
        # TODO: Make radius configurable
        radius = 3

        # Render the displayed image
        if display_mode == HSV_MODE_UNMASKED:
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        elif display_mode == HSV_MODE_MASKED:
            img = cv2.bitwise_and(frame, frame, mask=mask)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
        else:
            print("cleaning...")
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = cv2.inpaint(frame_rgb, mask, radius, cv2.INPAINT_TELEA)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2RGBA)

        imgtk = ImageTk.PhotoImage(image=Image.fromarray(img))
        # Prevent garbage collection
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)

    def save_and_quit(self):
        _, mask = self._get_mask()
        cv2.imwrite(str(self.out_file), mask)
        self.master.destroy()
