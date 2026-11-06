---
name: see
description: Lets an agent that reads images but no video see a recording frame by frame and measure a screen to the pixel. Use it to check an animation or a transition over time, compare two versions of one, find what differs between two screenshots, or measure sizes, padding and gaps on a screenshot against a design.
---

# Seeing video and images

The tool turns a video or an image into numbers first and labelled
images second. The numbers are exact and say where to look. The images
show what the numbers mean, each with a header that says what it is and
tags on its tiles, and each within the size Claude reads without
shrinking, 1,500 px on its long edge and about 1.1 megapixels. Run it
from the project root.

```bash
python3 .agents/skills/see/scripts/see.py report clip.mov out
```

It needs Python 3.9 or later and ffmpeg with ffprobe, nothing else.
Without ffmpeg every command says how to install it for the system and
exits 1. Every flag and every line it prints is in
[references/commands.md](references/commands.md).

## When to use it

- Something moves over time, an animation, a transition, a loading
  state or a scroll. Record it and run `report`.
- Two versions of one animation, before and after a change or the app
  against a reference. Record both and run `compare`.
- Two screenshots that should match, or a before and an after. Run
  `diff`.
- A screen to build or check against a design, its sizes, padding and
  gaps. Run `redline`, then `zoom` on an edge that matters.
- One frame of a recording to judge at full quality. Run `frame`.

## The way through

1. Read the printed numbers first. A burst's frames, a region's box, a
   held frame, a move of 4 px, a gap of 20 px are the findings.
2. Open only the image a line names for the moment that matters. Every
   image line names the frames or the moments its tiles show.
3. Judge pixels on a full quality image. A sheet scaled for an overview
   says so in its header and in its line, and `frame` gives any one
   frame at full quality.
4. Change the code, record or capture again, and run the same command,
   so the numbers show what the change did.

## Getting a video

The owner can hand over the path of a video in any format ffmpeg reads,
such as mp4, mov, mkv or webm. Or the agent records one itself.

- macOS. `screencapture -x -v -V 3 -R x,y,w,h clip.mov` records 3
  seconds of a rectangle given in points from the top left of the main
  display, and the video comes out in device px, 2 per point on a
  Retina display. The app that runs the command needs the Screen
  Recording permission, which the owner grants once in System Settings.
- Windows. ffmpeg records the desktop through gdigrab, in px from the
  top left of the main display. Record the desktop with offsets, since
  `-i title=...` drops a window's child controls. gdigrab may deliver a
  little under the rate asked, which the report reads from the frames'
  own times. The second command takes a still for `diff`, `redline` or
  `zoom`.

  ```bash
  ffmpeg -f gdigrab -framerate 60 -offset_x X -offset_y Y -video_size WxH -i desktop -t 3 -c:v libx264 -preset ultrafast -qp 0 clip.mkv
  ```

  ```bash
  ffmpeg -f gdigrab -offset_x X -offset_y Y -video_size WxH -i desktop -frames:v 1 -update 1 still.png
  ```

- Linux under X11. ffmpeg records through x11grab. Under Wayland
  x11grab sees nothing, so the owner records with the desktop's own
  recorder and hands over the file.

  ```bash
  ffmpeg -f x11grab -framerate 60 -video_size WxH -i :0.0+X,Y -t 3 -c:v libx264 -preset ultrafast -qp 0 clip.mkv
  ```

A recording shows what is on screen, so bring the app to the front
first. Start the recording, wait half a second, act, and leave a second
after, so the motion has still frames on both sides. Record lossless or
close to it, as `-qp 0` does, since the noise of heavy compression can
read as motion.

## Coordinates

Every number is device px, counted from the top left of the image or
the video, and a box is written `x,y,w,h`. A point is px divided by the
scale, and `--scale` is 2 unless given, the factor of a Retina display.
Give `--scale 1` for a display with no scaling, which a Windows desktop
at 100 percent is, and the display's own factor elsewhere, such as 1.5
on a Windows laptop at 150 percent.

## Limits

- The agent's own cursor is recorded when the agent drives the app with
  computer use, and it reads as a small region that follows the
  pointer. Move the pointer off the region before recording, or read
  past that region.
- A recording compressed hard carries noise that reads as motion. An
  everyday screen recording reads clean, and a lossless one always
  does.
- The last stretch of a strong ease out moves less than a pixel a
  frame, so the burst ends before the animation does. Read the curve
  from the frames that moved.
- A recorder that drops frames shows the drop as a held frame in the
  pacing, which may be the recorder and not the app. Record again to
  tell them apart.
- The redline finds elements by colour against the background, so a
  shadow, a gradient or a picture behind the content can join two
  elements or split one. Take its numbers as a strong first read, and
  check one that matters with `zoom`.
- A text box is measured by its ink, which holds the cap height and the
  descenders, never the line box the code sets. Text sits a little high
  of its box's centre for that reason, and the redline says so.
- The labels use the tool's own small font in capitals, since an ffmpeg
  build may carry no text filter.
