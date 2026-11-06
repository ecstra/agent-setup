"""A 5x7 bitmap font and a small RGB canvas, so every image carries its own labels with no library and no ffmpeg text filter, which some builds leave out."""

import math
from pathlib import Path

from . import media

GLYPHS = {
    "A": ".###.|#...#|#...#|#####|#...#|#...#|#...#",
    "B": "####.|#...#|#...#|####.|#...#|#...#|####.",
    "C": ".###.|#...#|#....|#....|#....|#...#|.###.",
    "D": "####.|#...#|#...#|#...#|#...#|#...#|####.",
    "E": "#####|#....|#....|####.|#....|#....|#####",
    "F": "#####|#....|#....|####.|#....|#....|#....",
    "G": ".###.|#...#|#....|#.###|#...#|#...#|.####",
    "H": "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    "I": ".###.|..#..|..#..|..#..|..#..|..#..|.###.",
    "J": "..###|...#.|...#.|...#.|...#.|#..#.|.##..",
    "K": "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#",
    "L": "#....|#....|#....|#....|#....|#....|#####",
    "M": "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#",
    "N": "#...#|#...#|##..#|#.#.#|#..##|#...#|#...#",
    "O": ".###.|#...#|#...#|#...#|#...#|#...#|.###.",
    "P": "####.|#...#|#...#|####.|#....|#....|#....",
    "Q": ".###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#",
    "R": "####.|#...#|#...#|####.|#.#..|#..#.|#...#",
    "S": ".####|#....|#....|.###.|....#|....#|####.",
    "T": "#####|..#..|..#..|..#..|..#..|..#..|..#..",
    "U": "#...#|#...#|#...#|#...#|#...#|#...#|.###.",
    "V": "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..",
    "W": "#...#|#...#|#...#|#.#.#|#.#.#|#.#.#|.#.#.",
    "X": "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    "Y": "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..",
    "Z": "#####|....#|...#.|..#..|.#...|#....|#####",
    "0": ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.",
    "1": "..#..|.##..|..#..|..#..|..#..|..#..|.###.",
    "2": ".###.|#...#|....#|...#.|..#..|.#...|#####",
    "3": "#####|...#.|..#..|...#.|....#|#...#|.###.",
    "4": "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.",
    "5": "#####|#....|####.|....#|....#|#...#|.###.",
    "6": "..##.|.#...|#....|####.|#...#|#...#|.###.",
    "7": "#####|....#|...#.|..#..|.#...|.#...|.#...",
    "8": ".###.|#...#|#...#|.###.|#...#|#...#|.###.",
    "9": ".###.|#...#|#...#|.####|....#|...#.|.##..",
    " ": ".....|.....|.....|.....|.....|.....|.....",
    ".": ".....|.....|.....|.....|.....|.##..|.##..",
    ",": ".....|.....|.....|.....|.##..|..#..|.#...",
    ":": ".....|.##..|.##..|.....|.##..|.##..|.....",
    "-": ".....|.....|.....|#####|.....|.....|.....",
    "+": ".....|..#..|..#..|#####|..#..|..#..|.....",
    "=": ".....|.....|#####|.....|#####|.....|.....",
    "(": "...#.|..#..|.#...|.#...|.#...|..#..|...#.",
    ")": ".#...|..#..|...#.|...#.|...#.|..#..|.#...",
    "/": ".....|....#|...#.|..#..|.#...|#....|.....",
    "%": "##...|##..#|...#.|..#..|.#...|#..##|...##",
    "#": ".#.#.|.#.#.|#####|.#.#.|#####|.#.#.|.#.#.",
    "<": "...#.|..#..|.#...|#....|.#...|..#..|...#.",
    ">": ".#...|..#..|...#.|....#|...#.|..#..|.#...",
    "_": ".....|.....|.....|.....|.....|.....|#####",
    "'": "..#..|..#..|.#...|.....|.....|.....|.....",
    "?": ".###.|#...#|....#|...#.|..#..|.....|..#..",
    "!": "..#..|..#..|..#..|..#..|..#..|.....|..#..",
    "[": ".###.|.#...|.#...|.#...|.#...|.#...|.###.",
    "]": ".###.|...#.|...#.|...#.|...#.|...#.|.###.",
    "*": ".....|#.#.#|.###.|#####|.###.|#.#.#|.....",
    "~": ".....|.....|.#...|#.#.#|...#.|.....|.....",
}
GLYPH_W, GLYPH_H = 5, 7
WHITE, DIM, HEAD = (255, 255, 255), (200, 200, 210), (24, 24, 28)
TAG_W = 300  # a tile is at least this wide, so its two tag lines fit in full size type
GAP = 8


def text_size(text: str, scale: int = 2) -> tuple:
    return len(text) * (GLYPH_W + 1) * scale, (GLYPH_H + 2) * scale


def wrap(text: str, width: int, scale: int = 2) -> list:
    """The text broken at spaces into lines that fit the width."""
    per_line = max(8, (width - 2 * scale) // ((GLYPH_W + 1) * scale))
    lines, line = [], ""
    for word in text.split(" "):
        if line and len(line) + 1 + len(word) > per_line:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}" if line else word
    return lines + ([line] if line else [])


class Canvas:
    def __init__(self, width: int, height: int, colour: tuple = (40, 40, 44)):
        self.width, self.height = width, height
        self.rgb = bytearray(bytes(colour) * (width * height))

    def rect(self, x: int, y: int, w: int, h: int, colour: tuple) -> None:
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, self.width), min(y + h, self.height)
        if x1 <= x0 or y1 <= y0:
            return
        line = bytes(colour) * (x1 - x0)
        for row in range(y0, y1):
            at = (row * self.width + x0) * 3
            self.rgb[at : at + len(line)] = line

    def outline(self, x: int, y: int, w: int, h: int, colour: tuple, thick: int = 2) -> None:
        self.rect(x, y, w, thick, colour)
        self.rect(x, y + h - thick, w, thick, colour)
        self.rect(x, y, thick, h, colour)
        self.rect(x + w - thick, y, thick, h, colour)

    def paste(self, x: int, y: int, w: int, h: int, rgb: bytes) -> None:
        x0, x1 = max(x, 0), min(x + w, self.width)
        if x1 <= x0:
            return
        for row in range(h):
            if 0 <= y + row < self.height:
                src = (row * w + (x0 - x)) * 3
                at = ((y + row) * self.width + x0) * 3
                self.rgb[at : at + (x1 - x0) * 3] = rgb[src : src + (x1 - x0) * 3]

    def text(self, x: int, y: int, text: str, scale: int = 2, colour: tuple = WHITE, background=(0, 0, 0)) -> None:
        """Text in capitals, on its own strip unless the background is None, so it reads over any picture."""
        if background is not None:
            w, h = text_size(text, scale)
            self.rect(x, y, w + scale, h, background)
        for i, char in enumerate(text.upper()):
            for gy, row in enumerate(GLYPHS.get(char, GLYPHS["?"]).split("|")):
                for gx, bit in enumerate(row):
                    if bit == "#":
                        self.rect(x + scale + (i * (GLYPH_W + 1) + gx) * scale, y + scale + gy * scale, scale, scale, colour)

    def save(self, path: Path) -> None:
        media.write_png(path, self.width, self.height, bytes(self.rgb))


def header_height(texts: list, width: int) -> int:
    return sum(len(wrap(text, width)) for text, _ in texts) * text_size("X")[1] + 6


def draw_header(canvas: Canvas, texts: list) -> int:
    """Lines of (text, colour) wrapped to the canvas on a dark band at its top, and the band's height."""
    height = header_height(texts, canvas.width)
    canvas.rect(0, 0, canvas.width, height, HEAD)
    y = 3
    for text, colour in texts:
        for line in wrap(text, canvas.width):
            canvas.text(2, y, line, 2, colour, None)
            y += text_size("X")[1]
    return height


def tagged_sheets(out: Path, stem: str, title: str, notes: list, tiles: list, tw: int, th: int) -> list:
    """Tiles in a grid, each under a two line tag, over as many sheets as the image budget needs, and the files written with their tile counts and sizes.

    A tile is (first tag line, second tag line, tag colour, rgb bytes of
    tw by th). The sheet's width and height keep to media.EDGE and AREA.
    """
    label_h = text_size("X")[1]
    cell_w, cell_h = max(tw, TAG_W), th + 2 * label_h + 4
    cols = max(1, min(len(tiles), (media.EDGE + GAP) // (cell_w + GAP)))
    width = cols * (cell_w + GAP) - GAP
    probe = [(title, WHITE), ("SHEET 10 OF 10", WHITE)] + [(note, DIM) for note in notes]
    rows_fit = max(1, int((media.AREA / width - header_height(probe, width)) // (cell_h + GAP)))
    per_sheet = cols * rows_fit
    chunks = [tiles[i : i + per_sheet] for i in range(0, len(tiles), per_sheet)]
    written = []
    for s, chunk in enumerate(chunks, 1):
        rows = math.ceil(len(chunk) / cols)
        texts = [(title, WHITE), (f"SHEET {s} OF {len(chunks)}", WHITE)] + [(note, DIM) for note in notes]
        head = header_height(texts, width)
        canvas = Canvas(width, head + rows * (cell_h + GAP), (70, 70, 76))
        draw_header(canvas, texts)
        for k, (top, bottom, colour, tile) in enumerate(chunk):
            cx, cy = (k % cols) * (cell_w + GAP), head + (k // cols) * (cell_h + GAP)
            canvas.rect(cx, cy, cell_w, 2 * label_h + 4, colour)
            canvas.text(cx + 2, cy + 1, top, 2, WHITE, None)
            canvas.text(cx + 2, cy + label_h + 2, bottom, 2, (225, 225, 235), None)
            canvas.rect(cx, cy + 2 * label_h + 4, cell_w, th, (50, 50, 54))
            canvas.paste(cx, cy + 2 * label_h + 4, tw, th, tile)
        path = out / f"{stem}-{s}.png"
        canvas.save(path)
        written.append((path, len(chunk), canvas.width, canvas.height))
    return written
