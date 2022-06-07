cleancredits
============

A very simple tool for removing on-screen text from video, using a user-provided mask.

Installation
============

pip install cleancredits

Usage
=====

cleancredits <video file> <video file extension> <mask file>

THIS PACKAGE MUST BE RUN FROM WITHIN THE SAME DIRECTORY THAT HOUSES THE VIDEO
FILE AND MASK FILE.

The video file extension should be the EXACT extension used on the file, and
should not include the dot. (E.g., if your file is named 'my_movie.mov,' you
should use 'mov' as your parameter.)

Optional Flags:

--radius - The number of pixels the inpaint algorithm uses for interpolation.
The default is 3, and this generally gives good results, but if you want to
experiment, go wild.

--framerate - The framerate of the video being cleaned. The default is 24fps.

--novideo - If this flag is selected, the cleaned frames will not be remuxed
into video. Use this option if you want to do your own muxing with options other
than the algorithm's default. The algorithm muxes video using ffmpeg's libx264
codec and yuv420p colorspace, which in testing were found to give the best
quality video while also still being recognizable by most editors and players.

Output
======

A folder containing all the cleaned frames of the video, and the cleaned
video, in .mp4 format.
