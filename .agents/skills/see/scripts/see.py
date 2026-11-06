#!/usr/bin/env python3
"""The see tool: a video or an image turned into numbers first and labelled images second, for an agent that reads images but no video.

Run as python3 .agents/skills/see/scripts/see.py <command>. It needs
ffmpeg and ffprobe and nothing else. Exit codes: 0 when it did the
thing, 1 when it refused and said why on standard error.
"""

import argparse
import sys
from pathlib import Path

from seelib import measure, media, motion, stills


def box(text: str) -> tuple:
    try:
        x, y, w, h = (int(v) for v in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{text}' is not a box, write x,y,w,h in device px") from None
    if w <= 0 or h <= 0:
        raise argparse.ArgumentTypeError(f"'{text}' has no area, its width and height must be above 0")
    return x, y, w, h


def parser() -> argparse.ArgumentParser:
    scale = argparse.ArgumentParser(add_help=False)
    scale.add_argument("--scale", type=float, default=2.0, help="device px per point, 2 on a Retina display, the default")
    top = argparse.ArgumentParser(prog="see", description="A video or an image as numbers first and labelled images second. Coordinates are device px.")
    commands = top.add_subparsers(dest="command", required=True)
    report = commands.add_parser("report", parents=[scale], help="every burst of motion in a video, the regions that moved, the pacing, tagged frame sheets and frame diffs")
    report.add_argument("video", type=Path)
    report.add_argument("out", type=Path, help="the folder the images go to")
    frame = commands.add_parser("frame", parents=[scale], help="one frame of a video at full quality")
    frame.add_argument("video", type=Path)
    frame.add_argument("index", type=int, help="the frame number, from 0")
    frame.add_argument("out", type=Path, help="the PNG to write")
    frame.add_argument("box", nargs="?", type=box, help="a crop, x,y,w,h")
    diff = commands.add_parser("diff", parents=[scale], help="what differs between two images, moved told apart from changed")
    diff.add_argument("a", type=Path)
    diff.add_argument("b", type=Path)
    diff.add_argument("out", type=Path, help="the folder the images go to")
    redline = commands.add_parser("redline", parents=[scale], help="the elements of an image, their sizes, the items inside and the gaps, drawn like a design tool's redline")
    redline.add_argument("image", type=Path)
    redline.add_argument("out", type=Path, help="the PNG to write")
    redline.add_argument("box", nargs="?", type=box, help="the region to measure, x,y,w,h")
    zoom = commands.add_parser("zoom", parents=[scale], help="a region zoomed with a pixel grid and rulers, its edges and colours as numbers")
    zoom.add_argument("out", type=Path, help="the PNG to write")
    zoom.add_argument("box", type=box, help="the region, x,y,w,h")
    zoom.add_argument("images", type=Path, nargs="+", help="one image, or two to compare")
    compare = commands.add_parser("compare", parents=[scale], help="two recordings lined up by their first motion and read side by side")
    compare.add_argument("a", type=Path)
    compare.add_argument("b", type=Path)
    compare.add_argument("out", type=Path, help="the folder the images go to")
    compare.add_argument("box", nargs="?", type=box, help="the region to compare, x,y,w,h, the moving region when left out")
    return top


def refuse_a_file_not_ours(args: argparse.Namespace) -> None:
    """Refuses an output PNG that is there already and was not written by this tool, since zoom takes its output first and a left out output would overwrite the first image."""
    if args.command in ("frame", "redline", "zoom") and args.out.exists() and not media.ours(args.out):
        raise media.SeeError(f"{args.out} is there already and this tool did not write it, so nothing was written, give the output a new name")


def main(argv: list) -> int:
    # a Windows pipe writes in the ANSI code page, which cannot spell every path, so the output is UTF-8 everywhere
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    args = parser().parse_args(argv)
    try:
        refuse_a_file_not_ours(args)
        media.require_ffmpeg()
        if args.command == "report":
            motion.report(args.video, args.out, args.scale)
        elif args.command == "frame":
            motion.frame(args.video, args.index, args.out, args.box, args.scale)
        elif args.command == "diff":
            stills.diff(args.a, args.b, args.out, args.scale)
        elif args.command == "redline":
            measure.redline(args.image, args.out, args.box, args.scale)
        elif args.command == "zoom":
            if len(args.images) > 2:
                raise media.SeeError("zoom takes one image, or two to compare")
            measure.zoom(args.out, args.box, args.images, args.scale)
        else:
            motion.compare(args.a, args.b, args.out, args.box, args.scale)
    except media.SeeError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
