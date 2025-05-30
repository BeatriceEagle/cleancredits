try:
    import tkinter as tk
    from tkinter import ttk
except ModuleNotFoundError as exc:
    tk = None
    ttk = None

import cv2
import numpy as np
from PIL import Image, ImageTk

from ..helpers import combine_masks, get_frame, render_mask

DISPLAY_MODE_MASK = "Areas to inpaint"
DISPLAY_MODE_DRAW = "Overrides"
DISPLAY_MODE_PREVIEW = "Preview"
DISPLAY_MODE_ORIGINAL = "Original"

DRAW_MODE_INCLUDE = "Always inpaint"
DRAW_MODE_EXCLUDE = "Never inpaint"
DRAW_MODE_RESET = "Reset"


FRAME_SETTINGS = frozenset(
    [
        "display_frame_number",
    ]
)

MASK_SETTINGS = frozenset(
    [
        "mask_frame_number",
        "mask_mode",
        "input_mask",
        "hue_min",
        "hue_max",
        "sat_min",
        "sat_max",
        "val_min",
        "val_max",
        "grow",
        "crop_left",
        "crop_top",
        "crop_right",
        "crop_bottom",
    ]
)

INPAINT_SETTINGS = frozenset(
    [
        "inpaint_radius",
    ]
)

DISPLAY_SETTINGS = frozenset(
    [
        "display_mode",
    ]
)

ZOOM_SETTINGS = frozenset(
    [
        "zoom_factor",
        "zoom_center_x",
        "zoom_center_y",
    ]
)

DRAW_SETTINGS = frozenset(
    [
        "draw_mode_enable",
        "draw_mode",
        "draw_size",
    ]
)


def get_zoom_crop(
    zoom_factor: float,
    zoom_center_x: int,
    zoom_center_y: int,
    video_width: int,
    video_height: int,
    max_width: int,
    max_height: int,
) -> (int, int, int, int):
    # zoom width and height are the dimensions of the box in the original
    # image that will be zoomed in (or out) and shown to the user. This should
    # be the largest possible width/height that will fit in the display box
    # after the zoom is applied.
    zoom_width = int(min(video_width * zoom_factor, max_width) / zoom_factor)
    zoom_height = int(min(video_height * zoom_factor, max_height) / zoom_factor)

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


def get_unzoomed_coords(
    zoomed_coords: (int, int),
    zoom_factor: float,
    zoom_center_x: int,
    zoom_center_y: int,
    video_width: int,
    video_height: int,
    max_width: int,
    max_height: int,
) -> (int, int):
    zoomed_x, zoomed_y = zoomed_coords
    crop_x, crop_y, _, _ = get_zoom_crop(
        zoom_factor,
        zoom_center_x,
        zoom_center_y,
        video_width,
        video_height,
        max_width,
        max_height,
    )
    # For the target pixel, compute the pixel in the original image.
    # crop_x and crop_y are the "origin" coordinates for the box in the
    # original image, so if we divide the scaled coordinates
    # by the zoom factor and add that to the "origin" coordinates,
    # we should get the original coordinates.
    img_x = int(zoomed_x // zoom_factor) + crop_x
    img_y = int(zoomed_y // zoom_factor) + crop_y
    return img_x, img_y


class VideoDisplay(object):
    def __init__(self, parent, cap, video_width, video_height):
        self.parent = parent
        self.root = parent.winfo_toplevel()
        self.canvas = tk.Canvas(parent, width=parent["width"], height=parent["height"])
        self.canvas.bind("<Motion>", self.handle_canvas_motion)
        self.canvas.bind("<Leave>", self.handle_canvas_leave)
        self.canvas.bind("<Button-1>", self.handle_canvas_drag)
        self.canvas.bind("<B1-Motion>", self.handle_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.handle_canvas_drag)
        self.canvas_img = self.canvas.create_image(0, 0, anchor=tk.NW)
        self.draw_cursor = None
        self.draw_prev = None

        self.cap = cap
        self.video_width = video_width
        self.video_height = video_height

        self.draw_mask = np.full((video_height, video_width), 127, np.uint8)
        self.draw_mask_changed = True

        self.new_settings = {}
        self.settings = {}

        self._display_frame = None
        self._mask_frame = None
        self._mask = None
        self._display = None

        self.display_frame_changed = True
        self.mask_changed = True
        self.overrides_changed = True
        self.inpaint_changed = True
        self.display_changed = True

        self.last_after_id = None

    def grid(self, *args, **kwargs):
        self.canvas.grid(*args, **kwargs)

    def clear_overrides(self):
        self.draw_mask = np.full((self.video_height, self.video_width), 127, np.uint8)
        self.draw_mask_changed = True
        self.schedule_render()

    def settings_changed(self, keys):
        if "input_mask" in keys:
            if not np.array_equal(
                self.new_settings["input_mask"], self.settings.get("input_mask")
            ):
                return True
        return any(
            self.new_settings[k] != self.settings.get(k)
            for k in keys - set(("input_mask",))
        )

    def mark_settings_changed(self, keys):
        self.settings |= {k: self.new_settings[k] for k in keys}

    def set(self, settings: dict):
        self.new_settings |= settings
        if self.settings_changed(settings.keys() & DRAW_SETTINGS):
            self.handle_draw_settings_change()
        if self.settings_changed(settings.keys() - DRAW_SETTINGS):
            self.schedule_render()

    def get_mask(self):
        return self._mask

    def get_mask_with_overrides(self):
        return self._mask_with_overrides

    def get_inpaint_radius(self):
        """
        get_inpaint_radius returns the inpaint radius set on mask_options,
        which is only guaranteed to be set in self.new_settings.
        """
        return self.new_settings["inpaint_radius"]

    def handle_draw_settings_change(self):
        if self.new_settings["draw_mode_enable"]:
            self.canvas.config(cursor="none")
        else:
            self.canvas.config(cursor="")
        self.mark_settings_changed(DRAW_SETTINGS)

    def handle_canvas_motion(self, event):
        if not self.settings.get("draw_mode_enable"):
            return

        radius = self.settings["draw_size"] * (self.settings["zoom_factor"] / 100) / 2
        coords = (
            event.x - radius,
            event.y - radius,
            event.x + radius,
            event.y + radius,
        )

        if self.draw_cursor is None:
            self.draw_cursor = self.canvas.create_oval(
                *coords, outline="black", width=5
            )
        else:
            self.canvas.coords(self.draw_cursor, *coords)

    def handle_canvas_leave(self, event):
        if self.draw_cursor is not None:
            self.canvas.delete(self.draw_cursor)
            self.draw_cursor = None

    def handle_canvas_drag(self, event):
        if not self.settings.get("draw_mode_enable"):
            return

        if event.type.name == "ButtonRelease":
            self.draw_prev = None
            return

        self.handle_canvas_motion(event)

        draw_size = self.settings["draw_size"]
        pt = get_unzoomed_coords(
            (event.x, event.y),
            self.settings["zoom_factor"] / 100,
            self.settings["zoom_center_x"],
            self.settings["zoom_center_y"],
            self.video_width,
            self.video_height,
            self.canvas.winfo_width(),
            self.canvas.winfo_height(),
        )
        draw_prev = self.draw_prev or pt

        if self.settings["draw_mode"] == DRAW_MODE_EXCLUDE:
            color = 0
        elif self.settings["draw_mode"] == DRAW_MODE_RESET:
            color = 127
        else:
            # DRAW_MODE_INCLUDE
            color = 255

        cv2.line(self.draw_mask, draw_prev, pt, color, draw_size)
        self.draw_prev = pt
        self.draw_mask_changed = True
        self.schedule_render()

    def schedule_render(self):
        if self.last_after_id is not None:
            self.root.after_cancel(self.last_after_id)
        # Don't update the display more than every 25 milliseconds.
        self.last_after_id = self.root.after(25, self.render)

    def render(self):
        """
        Render any changes to the display. We check what was last rendered against current settings to avoid
        rendering more than once per loop. We also short circuit after each potential step of the render to limit
        how much of the work happens in each loop.
        """
        if self.settings_changed(FRAME_SETTINGS):
            self._display_frame = get_frame(
                self.cap, self.new_settings["display_frame_number"]
            )
            self.mark_settings_changed(FRAME_SETTINGS)
            self.display_frame_changed = True
            self.root.after(1, self.render)
            return

        if self.settings_changed(MASK_SETTINGS):
            if self.settings_changed({"mask_frame_number"}):
                if (
                    self.new_settings["mask_frame_number"]
                    == self.new_settings["display_frame_number"]
                ):
                    self._mask_frame = self._display_frame
                else:
                    # This generally shouldn't happen, since mask options will always set the display frame number
                    # and mask frame number to the same value, but just in case!
                    self._mask_frame = get_frame(
                        self.cap, self.new_settings["mask_frame_number"]
                    )
            self._mask = render_mask(
                image=self._mask_frame,
                hue_min=self.new_settings["hue_min"],
                hue_max=self.new_settings["hue_max"],
                sat_min=self.new_settings["sat_min"],
                sat_max=self.new_settings["sat_max"],
                val_min=self.new_settings["val_min"],
                val_max=self.new_settings["val_max"],
                grow=self.new_settings["grow"],
                crop_left=self.new_settings["crop_left"],
                crop_top=self.new_settings["crop_top"],
                crop_right=self.new_settings["crop_right"],
                crop_bottom=self.new_settings["crop_bottom"],
            )
            self._mask_with_input = combine_masks(
                mode=self.new_settings["mask_mode"],
                top=self._mask,
                bottom=self.new_settings["input_mask"],
            )
            self.mark_settings_changed(MASK_SETTINGS)
            self.mask_changed = True
            self.root.after(1, self.render)
            return

        if self.draw_mask_changed or self.mask_changed:
            # Add include/exclude overrides to the mask
            _, include_mask = cv2.threshold(self.draw_mask, 128, 255, cv2.THRESH_BINARY)
            self._mask_with_overrides = cv2.bitwise_or(
                self._mask_with_input, include_mask
            )
            _, exclude_mask = cv2.threshold(self.draw_mask, 126, 255, cv2.THRESH_BINARY)
            self._mask_with_overrides = cv2.bitwise_and(
                self._mask_with_overrides, exclude_mask
            )
            self.mask_changed = False
            self.overrides_changed = True
            self.draw_mask_changed = False
            self.root.after(1, self.render)
            return

        # Inpainting is expensive so we skip it unless preview mode is active
        if self.new_settings["display_mode"] == DISPLAY_MODE_PREVIEW:
            if (
                self.settings_changed(INPAINT_SETTINGS)
                or self.overrides_changed
                or self.display_frame_changed
            ):
                frame_rgb = cv2.cvtColor(self._display_frame, cv2.COLOR_BGR2RGB)
                self._inpainted = cv2.inpaint(
                    frame_rgb,
                    self._mask_with_overrides,
                    self.new_settings["inpaint_radius"],
                    cv2.INPAINT_TELEA,
                )
                self.mark_settings_changed(INPAINT_SETTINGS)
                self.overrides_changed = False
                self.display_frame_changed = False
                self.inpaint_changed = True
                self.root.after(1, self.render)
                return
        elif self.overrides_changed or self.display_frame_changed:
            self.overrides_changed = False
            self.display_frame_changed = False
            self.inpaint_changed = True

        if self.settings_changed(DISPLAY_SETTINGS) or self.inpaint_changed:
            if self.new_settings["display_mode"] == DISPLAY_MODE_ORIGINAL:
                self._display = cv2.cvtColor(self._display_frame, cv2.COLOR_BGR2RGBA)
            elif self.new_settings["display_mode"] == DISPLAY_MODE_MASK:
                self._display = cv2.bitwise_and(
                    self._display_frame,
                    self._display_frame,
                    mask=self._mask_with_overrides,
                )
                self._display = cv2.cvtColor(self._display, cv2.COLOR_BGR2RGBA)
            elif self.new_settings["display_mode"] == DISPLAY_MODE_DRAW:
                self._display = self.draw_mask
            else:  # DISPLAY_MODE_PREVIEW
                self._display = cv2.cvtColor(self._inpainted, cv2.COLOR_RGB2RGBA)
            self.mark_settings_changed(DISPLAY_SETTINGS)
            self.inpaint_changed = False
            self.display_changed = True
            self.root.after(1, self.render)
            return

        if self.settings_changed(ZOOM_SETTINGS) or self.display_changed:
            # Crop to the specified center, then zoom
            zoom_factor = self.new_settings["zoom_factor"] / 100
            crop_x, crop_y, zoom_width, zoom_height = get_zoom_crop(
                zoom_factor,
                self.new_settings["zoom_center_x"],
                self.new_settings["zoom_center_y"],
                self.video_width,
                self.video_height,
                self.canvas.winfo_width(),
                self.canvas.winfo_height(),
            )
            img = self._display[
                crop_y : crop_y + zoom_height, crop_x : crop_x + zoom_width
            ]
            img = cv2.resize(
                img,
                None,
                fx=zoom_factor,
                fy=zoom_factor,
                interpolation=cv2.INTER_NEAREST,
            )

            # Store imgtk on self to prevent garbage collection
            self.imgtk = ImageTk.PhotoImage(image=Image.fromarray(img))

            self.canvas.itemconfig(self.canvas_img, image=self.imgtk)
            self.mark_settings_changed(ZOOM_SETTINGS)
            self.display_changed = False
