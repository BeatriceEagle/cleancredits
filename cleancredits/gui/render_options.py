import pathlib
import tempfile
from os import path

try:
    import tkinter as tk
    from tkinter import filedialog, ttk
except ModuleNotFoundError as exc:
    tk = None
    filedialog = None
    ttk = None

import cv2

from ..helpers import clean_frames, get_frame, join_frames
from .slider import Slider
from .video_display import DISPLAY_MODE_ORIGINAL


class RenderOptions(object):
    section_padding = {"pady": (50, 0)}

    def __init__(
        self,
        parent,
        video_path,
        frame_count,
        framerate,
        zoom_factor_fit,
        video_display,
        tabs,
    ):
        self.parent = parent
        self.root = parent.winfo_toplevel()
        self.video_path = video_path
        self.frame_count = frame_count
        self.framerate = framerate
        self.zoom_factor = zoom_factor_fit
        self.video_display = video_display
        self.tabs = tabs

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
        self.progress_label = ttk.Label(self.parent, wraplength=250)
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

    def save_mask(self):
        out_file = filedialog.asksaveasfilename(
            title="Save mask as",
        )
        if not out_file:
            return
        cv2.imwrite(str(out_file), self.video_display.get_mask_with_overrides())

    def save_render(self):
        self.disable_for_render()
        self.out_file = filedialog.asksaveasfilename(
            title="Render as",
        )
        if not self.out_file:
            self.enable_after_render()
            return

        start_frame = self.start_frame.get()
        end_frame = self.end_frame.get()
        frame_count = end_frame - start_frame + 1

        # Steps: clean each frame, render to a file, and join them into the output file.
        step_count = frame_count + 1

        self.progress_bar.config(
            value=0,
            maximum=step_count,
            takefocus=True,
        )

        self.progress_label.grid(
            row=2000, column=0, columnspan=3, **self.section_padding
        )
        self.progress_bar.grid(row=2001, column=0, columnspan=3)
        self.cleaned_frames_dir = tempfile.TemporaryDirectory()
        self.progress_label.config(text=f"Cleaning frame {start_frame}...")
        # Slight delay to make sure the UI can update
        self.root.after(10, lambda: self.save_render_clean_frame(start_frame))

    def save_render_clean_frame(self, frame_num):
        print(f"Cleaning frame {frame_num}...")
        frame = get_frame(self.video_display.cap, frame_num)
        mask = self.video_display.get_mask_with_overrides()
        # This is a little roundabout since ultimately inpaint_radius is set on the mask_options,
        # but we don't otherwise need access to mask_options.
        inpaint_radius = self.video_display.get_inpaint_radius()
        cleaned = cv2.inpaint(frame, mask, inpaint_radius, cv2.INPAINT_TELEA)
        cleaned = cv2.cvtColor(cleaned, cv2.COLOR_BGR2RGB)
        cleaned_frame = cleaned.astype(int)
        end_frame = self.end_frame.get()
        filename = path.join(
            self.cleaned_frames_dir.name,
            f"frame-{frame_num:0{len(str(end_frame))}}.png",
        )
        print(f"Writing {filename}...")
        cv2.imwrite(filename, cleaned_frame)

        self.progress_step()
        if frame_num < end_frame:
            self.progress_label.config(text=f"Cleaning frame {frame_num + 1}...")
            # Slight delay to make sure the UI can update
            self.root.after(10, lambda: self.save_render_clean_frame(frame_num + 1))
        else:
            self.progress_label.config(text=f"Muxing to {self.out_file}")
            # Slight delay to make sure the UI can update
            self.root.after(10, self.save_render_mux)

    def save_render_mux(self):
        print(f"Muxing to {self.out_file}")
        end_frame = self.end_frame.get()
        join_frames(
            pathlib.Path(self.cleaned_frames_dir.name),
            pathlib.Path(self.out_file),
            self.framerate,
            frame_filename=f"frame-%0{len(str(end_frame))}d.png",
            overwrite_output=True,
        )
        self.cleaned_frames_dir.cleanup()
        self.progress_step()
        self.progress_label.config(text=f"Done rendering {self.out_file}")
        print(f"Done rendering {self.out_file}")
        self.progress_bar.grid_forget()
        self.enable_after_render()

    def progress_step(self):
        self.progress_bar.step()
        print(f"Progress: {self.progress_bar['value']}/{self.progress_bar['maximum']}")

    def disable_for_render(self):
        self.tabs.tab(0, state="disabled")
        self.save_render_button.state(["disabled"])
        self.start_frame_slider.state(["disabled"])
        self.end_frame_slider.state(["disabled"])
        self.save_mask_button.state(["disabled"])

    def enable_after_render(self):
        self.tabs.tab(0, state="normal")
        self.save_render_button.state(["!disabled"])
        self.start_frame_slider.state(["!disabled"])
        self.end_frame_slider.state(["!disabled"])
        self.save_mask_button.state(["!disabled"])
