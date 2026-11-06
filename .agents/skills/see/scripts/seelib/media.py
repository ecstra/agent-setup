"""Everything the tool reads or writes goes through here: ffmpeg and ffprobe for videos and images, plain zlib for the PNGs it draws."""

import json
import shutil
import struct
import subprocess
import zlib
from pathlib import Path
from typing import Optional

# Claude shrinks an image past 1568 px on its long edge or past about 1.15 megapixels, so the tool keeps a margin under both
EDGE = 1500
AREA = 1_100_000
INSTALL = "ffmpeg and ffprobe are needed and not on this machine. Install them with brew install ffmpeg on macOS, winget install ffmpeg on Windows, or sudo apt install ffmpeg on Debian and Ubuntu, then run this again"


class SeeError(Exception):
    """A refusal the tool says in words and exits 1 on."""


def require_ffmpeg() -> None:
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        raise SeeError(INSTALL)


def require_file(path: Path) -> None:
    if not path.is_file():
        raise SeeError(f"no such file: {path}")


def ffmpeg(path: Path, args: list, stdin: Optional[bytes] = None) -> bytes:
    """What ffmpeg writes to standard output for these arguments, the path being the input it is asked to read."""
    done = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", *args], input=stdin, capture_output=True, check=False)
    if done.returncode != 0:
        reason = done.stderr.decode("utf-8", errors="replace").strip().splitlines()
        raise SeeError(f"ffmpeg cannot read {path}: {reason[-1] if reason else 'it gave no reason'}")
    return done.stdout


def probe(path: Path, entries: str) -> dict:
    done = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", entries, "-of", "json", str(path)], capture_output=True, check=False)
    if done.returncode != 0:
        raise SeeError(f"ffmpeg cannot read {path}: {done.stderr.decode('utf-8', errors='replace').strip() or 'ffprobe gave no reason'}")
    data = json.loads(done.stdout or b"{}")
    if not data.get("streams"):
        raise SeeError(f"ffmpeg cannot read {path}: it holds no picture")
    return data


class Video:
    """A video's size and the time of each of its frames, in seconds from its first."""

    def __init__(self, path: Path):
        require_file(path)
        data = probe(path, "stream=width,height,avg_frame_rate:frame=pts_time,best_effort_timestamp_time")
        stream = data["streams"][0]
        self.path = path
        self.width, self.height = int(stream["width"]), int(stream["height"])
        num, _, den = str(stream.get("avg_frame_rate", "0/1")).partition("/")
        rate = float(num or 0) / float(den or 1) if float(den or 1) else 0.0
        stamps = []
        for n, frame in enumerate(data.get("frames", [])):
            stamp = frame.get("pts_time", frame.get("best_effort_timestamp_time"))
            stamps.append(float(stamp) if stamp not in (None, "N/A") else (n / rate if rate else 0.0))
        if not stamps:
            raise SeeError(f"ffmpeg cannot read {path}: it holds no frame")
        self.times = [t - stamps[0] for t in stamps]
        gaps = sorted(b - a for a, b in zip(self.times, self.times[1:]) if b > a)
        if gaps:
            # a container rounds each time to the ms, so a 60 fps video's gaps read 16 or 17 ms, and their mean near the median is the true frame time
            median = gaps[len(gaps) // 2]
            near = [g for g in gaps if abs(g - median) <= 0.0015]
            self.period = sum(near) / len(near)
        else:
            self.period = 1 / rate if rate else 1 / 60

    def frames(self, indices: list, box: tuple) -> dict:
        """The listed frames cropped to the box, as rgb bytes by frame number."""
        x, y, w, h = box
        picks = "+".join(f"eq(n\\,{i})" for i in sorted(set(indices)))
        raw = ffmpeg(self.path, ["-i", str(self.path), "-vf", f"select='{picks}',crop={w}:{h}:{x}:{y}", "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
        size = w * h * 3
        return {index: raw[k * size : (k + 1) * size] for k, index in enumerate(sorted(set(indices)))}

    def change_cells(self, cell: int, threshold: int = 10) -> tuple:
        """Per pair of frames, the share of changed pixels in each cell of the grid, 255 for all, from ffmpeg so a full screen video stays fast."""
        cw, ch = -(-self.width // cell), -(-self.height // cell)
        graph = f"format=gray,tblend=all_mode=difference,lut=y='if(gt(val\\,{threshold})\\,255\\,0)',pad={cw * cell}:{ch * cell}:0:0:black,scale={cw}:{ch}:flags=area"
        raw = ffmpeg(self.path, ["-i", str(self.path), "-vf", graph, "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "gray", "-"])
        size = cw * ch
        return cw, ch, [raw[i : i + size] for i in range(0, len(raw) - size + 1, size)]


def image(path: Path) -> tuple:
    """An image as its width, height and rgb bytes."""
    require_file(path)
    data = probe(path, "stream=width,height")
    width, height = int(data["streams"][0]["width"]), int(data["streams"][0]["height"])
    raw = ffmpeg(path, ["-i", str(path), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    if len(raw) < width * height * 3:
        raise SeeError(f"ffmpeg cannot read {path}: it gave less picture than its size")
    return width, height, raw[: width * height * 3]


def crop(rgb: bytes, width: int, box: tuple) -> bytes:
    x, y, w, h = box
    return b"".join(rgb[((y + row) * width + x) * 3 : ((y + row) * width + x + w) * 3] for row in range(h))


def clip(box: tuple, width: int, height: int) -> tuple:
    """The box cut to the picture, and whether it had to be."""
    x, y, w, h = box
    x0, y0 = min(max(x, 0), width - 1), min(max(y, 0), height - 1)
    x1, y1 = min(max(x + w, x0 + 1), width), min(max(y + h, y0 + 1), height)
    clipped = (x0, y0, x1 - x0, y1 - y0)
    return clipped, clipped != tuple(box)


def scaled(rgb: bytes, w: int, h: int, factor: float) -> tuple:
    """Up by nearest neighbour or down by area average, through ffmpeg, as rgb bytes and the new size."""
    if factor == 1:
        return rgb, w, h
    nw, nh = max(1, round(w * factor)), max(1, round(h * factor))
    flags = "neighbor" if factor > 1 else "area"
    out = ffmpeg(Path("a drawing"), ["-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-i", "-", "-vf", f"scale={nw}:{nh}:flags={flags}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdin=rgb)
    return out, nw, nh


def write_png(path: Path, width: int, height: int, rgb: bytes) -> None:
    rows = b"".join(b"\x00" + rgb[y * width * 3 : (y + 1) * width * 3] for y in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows, 6)) + chunk(b"IEND", b""))


def luma(r: int, g: int, b: int) -> int:
    return (r * 299 + g * 587 + b * 114) // 1000


def apart(a: bytes, b: bytes) -> int:
    """The largest channel difference of two pixels."""
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]))


def changed_px(a: bytes, b: bytes, threshold: int = 14) -> int:
    return sum(1 for i in range(0, len(a), 3) if max(abs(a[i] - b[i]), abs(a[i + 1] - b[i + 1]), abs(a[i + 2] - b[i + 2])) > threshold)


def is_light(rgb: bytes) -> bool:
    """Whether a picture's commonest tone is light, sampled, so the overlays know which way ink runs."""
    sample = sorted(luma(*rgb[i : i + 3]) for i in range(0, len(rgb) - 2, 3 * 97))
    return bool(sample) and sample[len(sample) // 2] > 128


def overlay(a: bytes, b: bytes, light: bool, threshold: int = 14) -> bytes:
    """Two same sized pictures as one: red where only the first has ink, green where only the second does, yellow where both changed, grey the same."""
    out = bytearray(len(a))
    for i in range(0, len(a), 3):
        la, lb = luma(a[i], a[i + 1], a[i + 2]), luma(b[i], b[i + 1], b[i + 2])
        if max(abs(a[i] - b[i]), abs(a[i + 1] - b[i + 1]), abs(a[i + 2] - b[i + 2])) > threshold:
            ia, ib = (255 - la, 255 - lb) if light else (la, lb)
            out[i : i + 3] = bytes((max(ia, 40), max(ib, 40), 0))
        else:
            grey = 128 + (la - 128) // 3
            out[i : i + 3] = bytes((grey, grey, grey))
    return bytes(out)
