# cleancredits


A very simple tool for removing on-screen text from video, using a user-provided mask.

## Installation

```bash
pip install -U pip
pip install cleancredits
```

## Usage

### Generate HSV mask

```bash
cleancredits generate-hsv-mask [OPTIONS] VIDEO
```

Options:

```
-s, --start TIMECODE  Start timecode (HH:MM:SS[:frame]) in the input video
-e, --end TIMECODE    End timecode (HH:MM:SS[:frame]) in the input video
-i, --input FILE      Input mask. These pixels will always be present in the
                      output mask (unless explicitly excluded).
-o, --output FILE     Output mask to this location  [required]
--help                Show this message and exit.
```

This command will display a graphical interface for modifying a mask that allows isolating part of an image based on hue / saturation / value, as well as a bounding box. You can also manually add or exclude parts of an image.

You can layer combine masks for multiple colors or areas of credits by outputting a mask, then passing that as an `--input` to the generate-hsv-mask command.

### Clean credits

```bash
cleancredits [OPTIONS] VIDEO MASK
```

Arguments:

- `VIDEO`: Path to the video file being cleaned
- `MASK`: Path to the mask file. This should be a black and white png, where white indicates areas that will be removed and interpolated.

Options:

- `--start/--end`: The start/end timecodes (HH:MM:SS[:frame]) to process from the input video. Default: Start and end of the input video.

- `--radius`: The number of pixels the inpaint algorithm uses for interpolation. The default is 3, and this generally gives good results, but if you want to experiment, go wild.

- `--framerate`: The framerate (fps) of the video being cleaned. The default is 24.

- `--output PATH`: If this flag is selected, the cleaned frames will be remuxed into video and output at the specified `PATH`. You can omit this option if you want to do your own muxing. `cleancredits` muxes video using ffmpeg's libx264 codec and yuv420p colorspace, which in testing were found to give the best quality video while also still being recognizable by most editors and players. Outputting as a `.mp4` file is recommended.

Example:

```bash
# Takes a video.mkv and mask.png from the current directory and outputs
# output.mp4 to the current directory.
cleancredits video.mkv mask.png -o output.mp4
```

Output:

A folder containing all the cleaned frames of the video, and the cleaned
video.
