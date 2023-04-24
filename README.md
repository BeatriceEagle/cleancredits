# cleancredits


A very simple tool for removing on-screen text from video, using a user-provided mask.

## Installation

Install the latest released version:

```bash
pip install -U pip
pip install cleancredits
```

Or install the latest version from Github:

```bash
pip install git+https://github.com/BeatriceEagle/cleancredits@main
```

## Usage

### Generate HSV mask

```bash
cleancredits mask [OPTIONS] VIDEO
```

Generate a mask based on a video clip

Options:

```
  -s, --start TIMECODE     Start timecode (HH:MM:SS[:frame]) in the input
                           video
  -e, --end TIMECODE       End timecode (HH:MM:SS[:frame]) in the input video
  -i, --input FILE         Input mask. These pixels will always be present in
                           the output mask (unless explicitly excluded).
  -o, --output FILE        Output mask to this location  [required]
  --hue-min INTEGER RANGE  Minimum hue  [0<=x<=179]
  --hue-max INTEGER RANGE  Maximum hue  [0<=x<=179]
  --sat-min INTEGER RANGE  Minimum saturation  [0<=x<=255]
  --sat-max INTEGER RANGE  Maximum saturation  [0<=x<=255]
  --val-min INTEGER RANGE  Minimum value  [0<=x<=255]
  --val-max INTEGER RANGE  Maximum value  [0<=x<=255]
  --grow INTEGER RANGE     Grow amount  [0<=x<=20]
  --bbox-x1 INTEGER RANGE  Bounding box left x  [x>=0]
  --bbox-x2 INTEGER RANGE  Bounding box right x  [x>=0]
  --bbox-y1 INTEGER RANGE  Bounding box top y  [x>=0]
  --bbox-y2 INTEGER RANGE  Bounding box bottom y  [x>=0]
  --gui / --no-gui         Set --no-gui to directly render the mask without
                           displaying the GUI
  --help                   Show this message and exit.
```

This command will display a graphical interface for modifying a mask that allows isolating part of an image based on hue / saturation / value, as well as a bounding box. You can also manually add or exclude parts of an image.

You can layer combine masks for multiple colors or areas of credits by outputting a mask, then passing that as an `--input` to the `mask` command.

### Clean credits

```bash
cleancredits clean [OPTIONS] VIDEO MASK
```

Arguments:

- `VIDEO`: Path to the video file being cleaned
- `MASK`: Path to the mask file. This should be a black and white png, where white indicates areas that will be removed and interpolated.

Options:

- `--start/--end`: The start/end timecodes (HH:MM:SS[:frame]) to process from the input video. Default: Start and end of the input video.

- `--radius`: The number of pixels the inpaint algorithm uses for interpolation. The default is 3, and this generally gives good results, but if you want to experiment, go wild.

- `--framerate`: The framerate (fps) of the video being cleaned. The default is the input framerate.

- `--output PATH`: If this flag is selected, the cleaned frames will be remuxed into video and output at the specified `PATH`. You can omit this option if you want to do your own muxing. `cleancredits` muxes video using ffmpeg's libx264 codec and yuv420p colorspace, which in testing were found to give the best quality video while also still being recognizable by most editors and players. Outputting as a `.mp4` file is recommended.

Example:

```bash
# Takes a video.mkv and mask.png from the current directory and outputs
# output.mp4 to the current directory.
cleancredits clean video.mkv mask.png -o output.mp4
```

Output:

A folder containing all the cleaned frames of the video, and the cleaned
video.
