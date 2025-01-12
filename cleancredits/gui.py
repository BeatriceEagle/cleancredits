import copy
import math
import pathlib
import sys

try:
    import tkinter as tk
    from tkinter import colorchooser, ttk
except ModuleNotFoundError as exc:
    tk = None
    colorchooser = None
    ttk = None

import cv2
import numpy as np
from PIL import Image, ImageTk

from .helpers import get_frame, render_mask

HSV_MODE_UNMASKED = "Unmasked"
HSV_MODE_MASKED = "Masked"
HSV_MODE_PREVIEW = "Preview"

SECTION_PADDING = {"pady": (50, 0)}

COLORCHOOSER_FUZZ = 10

DRAW_MODE_NONE = "None"
DRAW_MODE_EXCLUDE = "Exclude"
DRAW_MODE_INCLUDE = "Include"
DRAW_MODE_RESET = "Reset"


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


class HSVMaskGUI(object):
    def __init__(
        self,
        cap,
        start_frame,
        end_frame,
        out_file: pathlib.Path,
        hue_min: int,
        hue_max: int,
        sat_min: int,
        sat_max: int,
        val_min: int,
        val_max: int,
        grow: int,
        bbox_x1: int,
        bbox_x2: int,
        bbox_y1: int,
        bbox_y2: int,
        input_mask=None,
    ):
        if tk is None:
            raise RuntimeError(
                "Could not initialize GUI. Python is not configured to support tkinter."
            )
        self.options_size = 300

        self.root = tk.Tk()
        self.root.title("HSV Mask")
        # Get the screen size of the screen the window is currently on.
        toplevel = tk.Toplevel(self.root)
        toplevel.geometry(self.root.geometry())
        toplevel.update_idletasks()
        toplevel.attributes("-fullscreen", True)
        toplevel.state("iconic")
        width, height = toplevel.geometry().split("+")[0].split("x")
        toplevel.destroy()
        toplevel.update()
        self.root.minsize(2 * self.options_size, self.options_size)
        self.root.maxsize(width, height)
        self.root.resizable(True, True)

        self.style = ttk.Style()
        self.style.configure("Video.TFrame")
        self.style.configure("Options.TFrame")
        self.style.configure("Main.TFrame")

        self.frame = ttk.Frame(self.root, style="Main.TFrame")
        self.frame.pack(fill="both", expand=True)

        self.cap = cap
        self.video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.out_file = out_file
        self.input_mask = input_mask
        self.draw_mask = np.full((self.video_height, self.video_width), 127, np.uint8)

        # Set up options display first so that it will not shrink.
        self.options_sidebar = ttk.Frame(self.frame, style="Options.TFrame")
        self.options_sidebar.pack(side="left", fill="y")

        self.options_canvas = tk.Canvas(self.options_sidebar)
        self.options_canvas.pack(side="left", fill="y")
        self.options_scrollbar = ttk.Scrollbar(
            self.options_sidebar, command=self.options_canvas.yview
        )
        self.options_scrollbar.pack(side="right", fill="y")

        self.options_frame = ttk.Frame(self.options_canvas)
        self.options_frame.columnconfigure(0, weight=1)
        self.options_frame.columnconfigure(1, weight=4)
        self.options_canvas.create_window(0, 0, window=self.options_frame, anchor=tk.NW)
        self.options_canvas.configure(yscrollcommand=self.options_scrollbar.set)

        # Change canvas size when widgets are added to the inner frame
        self.options_frame.bind(
            "<Configure>",
            lambda e: self.options_canvas.configure(
                scrollregion=self.options_canvas.bbox("all")
            ),
        )

        # Set up video display
        self.video_frame = ttk.Frame(self.frame, style="Video.TFrame")
        self.video_frame.pack(side="right", fill=None, expand=True)
        self.display = ttk.Label(self.video_frame)
        self.display.pack(fill="both", expand=True)
        self.display.bind("<Motion>", self.handle_display_motion)
        self.display.bind("<Button-1>", self.handle_display_drag)
        self.display.bind("<B1-Motion>", self.handle_display_drag)
        self.display.bind("<ButtonRelease-1>", self.handle_display_drag)

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
            from_=1,
            to=500,
            variable=self.zoom_factor,
            resolution=1,
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
            self.options_frame, text="Color chooser", command=self.handle_colorchooser
        ).grid(row=101, column=0, columnspan=2)
        # OpenCV hue goes from 0 to 179
        self.hue_min = tk.IntVar()
        self.hue_min.set(hue_min)
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
        self.hue_max.set(hue_max)
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
        self.sat_min.set(sat_min)
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
        self.sat_max.set(sat_max)
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
        self.val_min.set(val_min)
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
        self.val_max.set(val_max)
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
        self.grow.set(grow)
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
        self.bbox_x1.set(bbox_x1)
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
        self.bbox_y1.set(bbox_y1)
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
        self.bbox_x2.set(bbox_x2)
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
        self.bbox_y2.set(bbox_y2)
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

        # Make all options sidebar widgets handle mousewheel events.
        self.options_sidebar.bind("<MouseWheel>", self.handle_options_mousewheel)
        self.options_canvas.bind("<MouseWheel>", self.handle_options_mousewheel)
        self.options_frame.bind("<MouseWheel>", self.handle_options_mousewheel)
        for child in self.options_frame.children.values():
            child.bind("<MouseWheel>", self.handle_options_mousewheel)

        # First render is basically a frame change.
        # Temporarily assume the display width / height match the video size
        # so that we can get accurate measurements.
        self.display_width = self.video_width
        self.display_height = self.video_height
        self.handle_frame_change()

        # This will give us the actual window size.
        self.root.update()
        # Now set zoom factor to fit the whole image, then re-render.
        self.display_width = self.display.winfo_width()
        self.display_height = self.display.winfo_height()
        height_ratio = self.display_height / self.video_height
        width_ratio = self.display_width / self.video_width
        self.zoom_factor.set(max(1, int(min(height_ratio, width_ratio) * 100)))
        self.display.bind("<Configure>", self.handle_display_configure)

        self.render()

    def mainloop(self):
        self.root.mainloop()

    def handle_options_mousewheel(self, event):
        delta = -1 * event.delta
        if sys.platform != "darwin":
            delta = delta / 120
        self.options_canvas.yview_scroll(int(delta), "units")

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

        self._cache_mask()
        self._cache_display()
        self.render()

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

    def handle_frame_change(self, val=None):
        self.selected_frame = get_frame(self.cap, self.selected_frame_num.get())
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
        self._mask = render_mask(
            image=self.selected_frame,
            hue_min=self.hue_min.get(),
            hue_max=self.hue_max.get(),
            sat_min=self.sat_min.get(),
            sat_max=self.sat_max.get(),
            val_min=self.val_min.get(),
            val_max=self.val_max.get(),
            grow=self.grow.get(),
            bbox_x1=self.bbox_x1.get(),
            bbox_y1=self.bbox_y1.get(),
            bbox_x2=self.bbox_x2.get(),
            bbox_y2=self.bbox_y2.get(),
            input_mask=self.input_mask,
            draw_mask=self.draw_mask,
        )

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

    def save_and_quit(self):
        cv2.imwrite(str(self.out_file), self._mask)
        self.root.destroy()
