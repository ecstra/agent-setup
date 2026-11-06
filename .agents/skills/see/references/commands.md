# The see commands

Every command runs as `python3 .agents/skills/see/scripts/see.py
<command>` and takes `--scale`, the device px per point, 2 unless given.
Every coordinate is device px from the top left, and a box is written
`x,y,w,h`. Every path is read as the file it names, so a name such as
`10:11 shot.png` or `frame%03d.png` is never taken for a protocol or a
numbered sequence. Every line comes out in UTF-8 on every system, a
Windows pipe included, so any path prints whole. A command exits 0 when
it did its work and 1 when it refused, with the reason on standard
error, such as a missing file, a file ffmpeg cannot read, a frame number
past the end or ffmpeg itself missing.

Every image is a PNG within 1,500 px on its long edge and about 1.1
megapixels, and one shown below full quality says so in its header. A
small picture still gets a canvas at least 400 px wide, and a tile on a
sheet at least 300 px, so its header and its tags read.

No command writes over a file that is there already unless it is a PNG
the same command wrote, which the tool marks inside every PNG it
writes. So a run again into the same folder or name replaces its own
images, and a `zoom` whose output was left out never writes over the
first image it was given. The refusal reads `out.png is there already and is no zoom image
of this tool's, so nothing was written, give the output a new name`.
`frame`, `redline` and `zoom` refuse before any work, and `report`,
`diff` and `compare` refuse at that image, with the lines and the
images before it already out.

## report

```bash
python3 .agents/skills/see/scripts/see.py report <video> <out folder>
```

Finds every burst of motion in a video and writes tagged sheets of the
frames and of the frame diffs where each burst moved.

It prints these lines in order.

- `video clip.mov: 45 frames, 840x760 px (420x380 pt at 2x), 733 ms, a
  frame every 16.7 ms`
- `1 burst of motion, 26 frames show no change past the noise floor`,
  or `no motion past the noise floor, so no sheets were written`, where
  the command ends.
- Per burst, its frames and its time, from the still frame before it to
  the last frame that moved, `burst 1: frames 6 to 24, 100 to 400 ms
  (300 ms), 18 frames changed`.
- Its pacing, the median and the longest gap between changed frames,
  each counted in whole frame times, and each hold, a gap over one and a
  half times the median, so an app that draws every other frame of the
  recording holds nothing. The first eight holds are named and the rest
  counted, `pacing: a change every 16.7 ms at the median, the longest
  gap 50.0 ms, 1 hold over 25 ms: before F22 (50 ms, 2 frames held)`.
- Every region that moved, largest first, each a box in px and in pt,
  `region 1: x 96 y 480 w 576 h 80 px (x 48 y 240 w 288 h 40 pt)`. A
  region too big to show at full quality ends `, key frames only,
  scaled`, and the third and every one after it end `, no sheets, only
  the two largest regions get them, so take its frames with frame and a
  crop`.
- Under each of the two largest regions, a line per sheet written,
  naming the frames its tiles show, `image out/burst-1-region-1-frames-1.png:
  F6 to F15, 10 tiles, 1192x834`.
- A table of every changed frame, its ms from the start, its ms since
  the row before and the pixels it changed over the whole frame,
  counted the way the last paragraph of this section says.

The sheets of a region are `burst-<n>-region-<r>-frames-<s>.png` and
`burst-<n>-region-<r>-diffs-<s>.png`. Each shows the region with up to
8 px around it, so an edge that moved is never cut, and its header
gives that wider crop. A frames sheet holds the frame before the
motion, tagged gold, then every frame where the region changed, each
tagged with its frame number, its ms from the start, and the ms and
pixels changed since the tile before it. A tag counts the pixels of the
sheet's crop past 14 of 255 in any channel, as `diff` does, so a fade's
tags can read 0 where the table counts it. A diffs sheet holds what
changed from each tile to the next, red only in the earlier frame,
green only in the later, yellow changed in both and grey the same. A
region too big for full quality gets an overview of up to six key
frames instead, the one before, those that changed a third of the peak
or more, and the last, with every changed frame still in the table.

What counts as motion is fixed, and it is read in 16 px cells. A cell
moves when about 3 of its 256 pixels step past 10 of 255 grey levels
from the frame before, and counts the pixels that stepped. A cell no
pixel stepped in moves too when its mean grey still changes and has
drifted 4 levels or more over the last 6 frames, as a fade or a faint
element does, and counts whole, every pixel in it. A frame moves when
it counts 12 changed px or more, so a few pixels of encoder noise stay
still and a 2 by 20 px cursor counts. Frames that move within 250 ms of
each other make one burst, and moving cells within 2 cells of each
other make one region. How rough the counts of a faint change are is
under the sheet's [Limits](../SKILL.md#limits).

## frame

```bash
python3 .agents/skills/see/scripts/see.py frame <video> <n> <out.png> [x,y,w,h]
```

Writes frame `n`, counted from 0, at full quality, cropped to the box
when one is given, under a header with its number, time, crop and
quality. It prints `image out.png: frame 20 at 333 ms, full quality,
840x802`. A crop past the frame's edge is clipped and says so, `the crop
is clipped to x 300 y 200 w 20 h 40 to fit the frame`. A crop too big
for full quality is scaled and says by how much.

## diff

```bash
python3 .agents/skills/see/scripts/see.py diff <a> <b> <out folder>
```

Finds the pixels of two images that differ past 14 of 255 in any
channel, groups them into boxes, and names what each box did. It prints
each image's size first, `a before.png: 840x760 px`, and two images of
different sizes are compared over their shared top left area, which it
says next, `the sizes differ, so only the top left 840x740 is compared`.

Then it prints the count over that area and whether its background is
light or dark, `7121 of 621600 px differ past 14 of 255, on a light
background`, and a line for every change, largest first, numbered as
on the overview.

- `#1: x 122 y 193 w 631 h 73 px (x 61 y 96.5 w 315.5 h 36.5 pt), 6615
  px differ: moved down 2 px (1 pt), the same shape once aligned,
  colour off by up to 7 of 255`
- `moved down 4 px (2 pt) and changed, 506 px still differ once
  aligned`
- `new in b, nothing was there in a`, and `gone from b, it was there in
  a`
- `changed in place`

A move is looked for up to 8 px each way, up or down first, and a
sideways move counts only where it halves what that leaves. A box is
named moved where a twentieth or less of what differed still differs
once aligned, and moved and changed where a quarter or less does. A solid
element that moves differs only along its leading and trailing edges,
so the boxes of those edges are joined into one change wherever one
move lines the joined box up whole, while two elements that moved with
still content between them stay two. Identical images print `the
images are the same past 14 of 255` and write nothing.

It writes `diff-overview.png`, the picture with every change boxed and
numbered, and `diff-change-<n>.png` for each of the 12 largest changes,
with A, B, their overlay and, for a move, B shifted back into line,
zoomed up to 8 times where that fits. More than 12 changes end with
`changes #13 to #18 have no image of their own, they are numbered on
the overview, and zoom shows any of them`. In the overlay red is only
in A and green only in B, the colours chosen for a light or a dark
background.

## redline

```bash
python3 .agents/skills/see/scripts/see.py redline <image> <out.png> [x,y,w,h]
```

Measures the elements of an image, or of the region given, the way a
design tool's redline does, and draws the same numbers on the image.

- The first line names the region, its background and the scale, and
  where nothing stands out it says `nothing stands out from the
  background in the region`.
- An element is a shape that stands out from the background by more
  than 8 of 255, `E1: x 80 y 80, 724 x 329 px (362 x 164.5 pt) solid,
  724 x 329 px with its soft edge, fill #ffffff`, or one with `no fill,
  an outline or bare ink`. Solid is its size where it is fully drawn,
  and the soft edge adds its antialiased rim.
- The items inside an element come under it, `E1.1: x 124 y 129, 266 x
  31 px`, with how they are laid out, `in a row: padding left 28, right
  60, gaps 16`, or `in a column: padding top 49, bottom 42, gaps 33,
  36`, then the tops and bottoms or the lefts and rights of each item.
  Items in neither a row nor a column each say how far they sit from
  each side, `E1.1 sits 20 from the left, 20 from the top, 40 from the
  right, 66 from the bottom`. Pieces within 14 px of each other are one
  item, so a label's letters and words stay one. A filled item is read one level further in, `E1.3
  has the fill #3b5bdb and holds`, with its own items and layout.
- How far a row's items sit off its vertical centre, `off the vertical
  centre: -0.5`, which text does by its descenders.
- The gap from each element to the nearest one on its right and the
  nearest one below it, `gap E1 to E2, across: 20 px (10 pt)` or `gap
  E1 to E3, down: 20 px (10 pt)`, then the edges elements share,
  `aligned tops: E1, E2 at y 80`, and the same for bottoms.
- An element the region cuts says `cut by the region's edge, so its size
  is not its own`, and a region past the image's edge is clipped and
  says so.
- The last line names the image, `image out.png: the redline, 700x636`,
  drawn at up to twice the size by a whole number where that fits.

## zoom

```bash
python3 .agents/skills/see/scripts/see.py zoom <out.png> <x,y,w,h> <image> [image2]
```

Writes the region zoomed by nearest neighbour, by the largest whole
number up to 16 that fits, with rulers in the whole image's px, a dark
line every 10 px and, from 6 times up, a thin line for every pixel,
beside the same region of the second image when one is given. Two
images of different sizes are read over their shared top left area,
and a region past its edge is clipped and says so. A zoom shows every pixel or none, so a region that does not fit the
image budget at its own size is refused, `the region is too big to
zoom, since a zoom shows every pixel and 1280 x 824 px does not fit the
image budget, give a smaller region`, and so are more than two images.

Per image it prints the background, `shot.png: background #ffffff`,
the ink box of what differs from it by more than 24, the commonest ink
colours, and the coverage of the ink's left and top edges, read along
the line nearest the ink's middle that reaches each edge, or `no ink
in the region`.

- `ink from x 40 to 89, y 60 to 89: 50 x 30 px = 25 x 15 pt`
- `most common ink colours: #28282c 700 px, #6e6e76 300 px`
- `left edge along y 74: coverage 37:0.00 38:0.00 39:0.00 40:1.00
  41:1.00 42:1.00, half covered at 40`

Then it names the image, `image out.png: the zoom, 1006x772`. For two
images the last line gives how the second's ink edges moved against
the first's, `second against first: top +2 px, bottom +6 px, pt = px /
2`, or says `the ink box is the same`.

## compare

```bash
python3 .agents/skills/see/scripts/see.py compare <a> <b> <out folder> [x,y,w,h]
```

Lines two recordings of one size up at the frame before each one's
first motion and reads them side by side at the same ms from there,
over the box given or over every region either one moved in. With a
box, the first motion is the first inside it, so the pointer on its
way to the box never sets the start. Two recordings of different sizes
are refused, `the two recordings differ in size, so they cannot be laid
side by side, record both at one size`.

- `a before.mov: 60 frames, 320x240 px`, and the same line for b.
- `a moves from F13 and b from F21, lined up there`
- `compared over x 16 y 96 w 256 h 48 px (x 8 y 48 w 128 h 24 pt)`,
  ending `, clipped to the frame` where the box went past it.
- A row per frame of a, its ms from the start, the frame of each and
  the pixels that differ past 14 of 255, `+50 ms  F15    F23    640`.
  The frame of b is the last one b showed by that moment, so a frame
  b's recorder dropped holds b's frame before it, and the rows stop
  where either recording ends.
- `the most apart at +250 ms, 3200 px differ`, then `they match again
  from +400 ms`, `they still differ at the end of the shorter
  recording` or `they match all the way`.
- A line per sheet, naming the moments it shows, `image
  out/compare-1.png: +0 ms to +200 ms, 13 tiles, 780x1380`.

The table and the sheets stop three rows into the match, the row where
they match again and two after it. Each tile of `compare-<s>.png` is
one moment, a on the left, b in the middle and their overlay on the
right, red only in a and green only in b.
