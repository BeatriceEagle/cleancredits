import pathlib
import tempfile

try:
    import tkinter as tk
    from tkinter import filedialog, ttk
except ModuleNotFoundError as exc:
    tk = None
    filedialog = None
    ttk = None

import cv2

from ..helpers import clean_frames, join_frames, split_frames
from .slider import Slider
from .video_display import DISPLAY_MODE_ORIGINAL


class RenderOptions(object):
    section_padding = {"pady": (50, 0)}

    def __init__(
        self, parent, video_path, frame_count, framerate, zoom_factor_fit, video_display
    ):
        self.parent = parent
        self.video_path = video_path
        self.frame_count = frame_count
        self.framerate = framerate
        self.zoom_factor = zoom_factor_fit
        self.video_display = video_display

        self.start_frame = tk.IntVar(value=0)
        self.end_frame = tk.IntVar(value=self.frame_count - 1)
        self.last_frame_changed = "start"

    def build(self):
        self.start_frame_slider = Slider(
            self.parent,
            "Start frame",
            from_=0,
            to=self.frame_count - 1,
            variable=self.start_frame,
            command=self.handle_start_frame_change,
        )

        self.end_frame_slider = Slider(
            self.parent,
            "End frame",
            from_=0,
            to=self.frame_count - 1,
            variable=self.end_frame,
            command=self.handle_end_frame_change,
        )

        self.button_frame = ttk.Frame(self.parent)
        self.save_render_button = ttk.Button(
            self.button_frame, text="Render", command=self.save_render
        )
        self.save_mask_button = ttk.Button(
            self.button_frame, text="Export final mask", command=self.save_mask
        )
        self.progress_label = ttk.Label(self.parent)
        self.progress_bar = ttk.Progressbar(
            self.parent,
            orient="horizontal",
            mode="determinate",
        )

        self.start_frame_slider.grid(row=0, column=0)
        self.end_frame_slider.grid(row=1, column=0)
        self.button_frame.grid(row=1000, column=0, columnspan=3, **self.section_padding)
        self.save_render_button.grid(row=0, column=0)
        self.save_mask_button.grid(row=0, column=1)

    def handle_selected(self):
        if self.last_frame_changed == "start":
            self.handle_start_frame_change()
        else:
            self.handle_end_frame_change()

    def handle_start_frame_change(self, val=None):
        self.last_frame_changed = "start"
        self.video_display.set(
            {
                "display_mode": DISPLAY_MODE_ORIGINAL,
                "frame_number": self.start_frame.get(),
                "zoom_factor": self.zoom_factor,
            }
        )
        self.progress_label.grid_forget()
        self.progress_bar.grid_forget()

    def handle_end_frame_change(self, val=None):
        self.last_frame_changed = "end"
        self.video_display.set(
            {
                "display_mode": DISPLAY_MODE_ORIGINAL,
                "frame_number": self.end_frame.get(),
                "zoom_factor": self.zoom_factor,
            }
        )
        self.progress_label.grid_forget()
        self.progress_bar.grid_forget()

    def save_render(self):
        out_file = filedialog.asksaveasfilename(
            title="Render as",
        )
        if not out_file:
            return

        start_frame = self.start_frame.get()
        end_frame = self.end_frame.get()
        frame_count = end_frame - start_frame + 1

        # Steps: convert each frame to an image, clean each frame, and join them into the output file.
        step_count = (frame_count * 2) + 1

        self.progress_label.config(text="Splitting frames...")
        print("Splitting frames...")
        self.progress_bar.config(
            value=0,
            maximum=step_count,
            takefocus=True,
        )

        self.progress_label.grid(
            row=2000, column=0, columnspan=2, **self.section_padding
        )
        self.progress_bar.grid(row=2001, column=0, columnspan=2)

        with tempfile.TemporaryDirectory() as frames_dir:
            with tempfile.TemporaryDirectory() as cleaned_frames_dir:
                split_frames(
                    pathlib.Path(self.video_path),
                    pathlib.Path(frames_dir),
                    start=f"{start_frame / self.framerate}s",
                    end=f"{end_frame / self.framerate}s",
                )

                self.progress_bar.step(frame_count)

                mask = self.video_display.get_mask()
                # This is a little roundabout since ultimately this is set on the mask_options,
                # but we don't otherwise need access to mask_options.
                inpaint_radius = self.video_display.get_inpaint_radius()
                for _, cleaned_frame_path in clean_frames(
                    mask,
                    pathlib.Path(frames_dir),
                    pathlib.Path(cleaned_frames_dir),
                    inpaint_radius,
                ):
                    self.progress_label.config(
                        text=f"Cleaning frames... {cleaned_frame_path.name}"
                    )
                    print(f"Cleaning frames... {cleaned_frame_path.name}")
                    self.progress_bar.step()

                self.progress_label.config(text=f"Muxing to {out_file}")
                print(f"Muxing to {out_file}")
                self.progress_bar.step()

                join_frames(
                    pathlib.Path(cleaned_frames_dir),
                    pathlib.Path(out_file),
                    self.framerate,
                    overwrite_output=True,
                )

        self.progress_label.config(text=f"Done rendering {out_file}")
        print(f"Done rendering {out_file}")
        self.progress_bar.config(takefocus=False)

    def save_mask(self):
        out_file = filedialog.asksaveasfilename(
            title="Save mask as",
        )
        if not out_file:
            return
        cv2.imwrite(str(out_file), self.video_display.get_mask())
