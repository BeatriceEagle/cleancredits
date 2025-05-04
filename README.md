# cleancredits

A tool for removing on-screen text from video.

## Installation

cleancredits has the following system dependencies:

- [ffmpeg](https://ffmpeg.org/) for video manipulation
- [tkinter](https://docs.python.org/3/library/tkinter.html) for the GUI

Once those dependencies are installed:

1. Mac OS: Install [homebrew](https://brew.sh/) and run `brew install python-tk` to install tkinter bindings.
2. Install [pipx](https://pypa.github.io/pipx/), a package manager for python tools.
3. Install the latest released version of cleancredits:

   ```bash
   pipx install cleancredits
   ```

   Or install the latest version from Github:

   ```bash
   pipx install git+https://github.com/BeatriceEagle/cleancredits@main
   ```

## Basic usage

Run `cleancredits` with no arguments to open the editing GUI. You will need to select the video clip you want to work with before the interface will open.

There are two tabs: one for modifying mask layers, and one for rendering the cleaned version of the clip.

### Mask tab

The area included in the mask will be removed and "inpainted" (that is, replaced with colors chosen by nearby pixels). The mask should aim to include all of the text you want to remove and nothing else.

The mask tab has the following controls:

1. Layer. Allows adding up to 5 mask layers that will be stacked on top of each other to determine the final mask. This is useful, for example, if there are multiple colors of text that you want to remove at once.
2. Frame. This determines the frame to use when building the mask for the current layer.
3. Display mode. What will get displayed on the right-hand side. The values have the following meanings:
   * Areas to inpaint. Display the areas that will be inpainted - that is, the final mask - assuming that the current layer is the final layer. For example, if you have layer 3 selected, this will take layers 1 & 2 into account but not layers 4 & 5.
   * Preview. Display what this frame would look like if inpainted. This mode will be slower to render.
   * Overrides. Show only the overrides layer (see later in this section for details.)
   * Original. Show the original frame.
4. Display zoom. Modify the zoom settings for the right-hand display. This does not modify the mask, just the view.
5. Hue / Saturation / Value. Set what ranges of colors should be considered for the current mask layer.
6. Crop. Select what areas of the frame will be considered for the current mask layer. This can be useful if other parts of the image have similar colors to the text you want to remove.
7. Mask mode. Select whether the current layer should determine places that will always / never be inpainted. Each layer will override the layers underneath it.
8. Grow. Add additional pixels to the edge of the current mask layer's selected areas. This can be useful to ensure that video compression artifacts don't negatively impact the inpainting process.
9. Overrides. Manually draw overrides to force specific areas to always / never be inpainted. This will be applied after all mask layers.
10. Inpaint radius. How many neighboring pixels to use to calculate the right color for each pixel. The larger this number, the slower rendering will be.

![Screenshot of Mask tab GUI](/preview-mask.png)

### Render tab

Choose the start and end frames to remove the text from, then click "Render" to output the cleaned video. You can also export the final mask for usage outside the GUI.

![Screenshot of Mask tab GUI](/preview-render.png)

## Advanced usage

You can also run subcommands in terminal to generate a mask and to use the mask to remove and inpaint an area.

### Generate HSV mask

```bash
cleancredits mask [OPTIONS] VIDEO
```

Generate a mask based on a video clip

Options:

```
  -s, --start TIMECODE         Start timecode (HH:MM:SS[:frame]) in the input
                               video
  -e, --end TIMECODE           End timecode (HH:MM:SS[:frame]) in the input
                               video
  -i, --input FILE             Input mask. These pixels will always be present
                               in the output mask (unless explicitly
                               excluded).
  -o, --output FILE            Output mask to this location  [required]
  --hue-min INTEGER RANGE      Minimum hue  [0<=x<=179]
  --hue-max INTEGER RANGE      Maximum hue  [0<=x<=179]
  --sat-min INTEGER RANGE      Minimum saturation  [0<=x<=255]
  --sat-max INTEGER RANGE      Maximum saturation  [0<=x<=255]
  --val-min INTEGER RANGE      Minimum value  [0<=x<=255]
  --val-max INTEGER RANGE      Maximum value  [0<=x<=255]
  --grow INTEGER RANGE         Grow amount  [0<=x<=20]
  --crop-left INTEGER RANGE    Crop left  [x>=0]
  --crop-right INTEGER RANGE   Crop right  [x>=0]
  --crop-top INTEGER RANGE     Crop top  [x>=0]
  --crop-bottom INTEGER RANGE  Crop bottom  [x>=0]
  --help                       Show this message and exit.
```

This command will display a graphical interface for modifying a mask that allows isolating part of an image based on hue / saturation / value, as well as a bounding box. You can also manually add or exclude parts of an image.

You can layer combine masks for multiple colors or areas of text by outputting a mask, then passing that as an `--input` to the `mask` command.

### Remove & inpaint

```bash
cleancredits clean [OPTIONS] VIDEO MASK
```

Arguments:

- `VIDEO`: Path to the video file being cleaned
- `MASK`: Path to the mask file. This should be a black and white png, where white indicates areas that will be removed and interpolated. You can generate a mask like this using the `cleancredits mask` command or the GUI's "Export final mask" button, or any image editing tool.

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

RoyaltyFreeVideos license
=========================

Footage used in screenshots and tests is courtesy of [RoyaltyFreeVideos](https://www.youtube.com/c/RoyaltyFreeVideos/about). At the time the footage was pulled, this page read:

```
Please feel free to use any of the videos on this channel for personal and commercial use without credit and without payment in your video projects. The only thing you may not do with our videos is re-upload them in raw format outside of your own creations. A credit or link back to our channel is appreciated though is not necessary.
```

Videos used:

- [Horses In Field](https://www.youtube.com/watch?v=ieI8DDNLBgs)
