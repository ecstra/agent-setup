"""A video read for what moved, where and how evenly, as a report and tagged sheets of frames and of frame diffs, and two recordings read side by side."""

import math
from pathlib import Path

from . import draw, media

CELL = 16
# a cell this changed is about 3 pixels of its 256, past the noise a compressed still frame carries
CELL_FLOOR = 3
FRAME_FLOOR = 12
BURST_GAP = 0.25
HOLDS_NAMED = 8
GOLD, BLUE, TEAL = (120, 90, 0), (30, 50, 110), (20, 80, 60)


def pt(value: float, scale: float) -> str:
    return f"{value / scale:g}"


def box_text(box: tuple, scale: float) -> str:
    x, y, w, h = box
    return f"x {x} y {y} w {w} h {h} px (x {pt(x, scale)} y {pt(y, scale)} w {pt(w, scale)} h {pt(h, scale)} pt)"


def moving_pairs(video: media.Video) -> tuple:
    """Per frame after the first, the pixels it changed past the noise floor and its live cells, and the grid's size."""
    cw, ch, pairs = video.change_cells(CELL)
    moving = []
    for i, cells in enumerate(pairs):
        live = bytes(c if c >= CELL_FLOOR else 0 for c in cells)
        moving.append((i + 1, round(sum(live) / 255 * CELL * CELL), live))
    return cw, ch, moving


def bursts_of(video: media.Video, moving: list) -> list:
    bursts = []
    for frame, changed, live in moving:
        if changed < FRAME_FLOOR:
            continue
        if bursts and video.times[frame] - video.times[bursts[-1][-1][0]] <= BURST_GAP:
            bursts[-1].append((frame, changed, live))
        else:
            bursts.append([(frame, changed, live)])
    return bursts


def regions_of(cells: bytes, cw: int, ch: int) -> list:
    """Boxes of 8 connected live cells, in cells, those two cells apart or less joined, largest first."""
    seen = bytearray(cw * ch)
    boxes = []
    for start in range(cw * ch):
        if not cells[start] or seen[start]:
            continue
        seen[start] = 1
        stack, count = [start], 0
        x0 = x1 = start % cw
        y0 = y1 = start // cw
        while stack:
            at = stack.pop()
            count += 1
            x, y = at % cw, at // cw
            x0, x1, y0, y1 = min(x0, x), max(x1, x), min(y0, y), max(y1, y)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < cw and 0 <= ny < ch and cells[ny * cw + nx] and not seen[ny * cw + nx]:
                        seen[ny * cw + nx] = 1
                        stack.append(ny * cw + nx)
        boxes.append([x0, y0, x1, y1, count])
    joined = True
    while joined:
        joined = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                if a[0] - 2 <= b[2] and b[0] - 2 <= a[2] and a[1] - 2 <= b[3] and b[1] - 2 <= a[3]:
                    boxes[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]), a[4] + b[4]]
                    del boxes[j]
                    joined = True
                    break
            if joined:
                break
    return sorted(boxes, key=lambda b: -b[4])


def union(burst: list, size: int) -> bytes:
    cells = bytearray(size)
    for _, _, live in burst:
        for k, c in enumerate(live):
            if c:
                cells[k] = 1
    return bytes(cells)


def pacing(video: media.Video, burst: list) -> str:
    stamps = [video.times[f] for f, _, _ in burst]
    # each gap counted in whole frame times, so the ms a container rounds to does not read as a stutter
    frame_ms = 1000 * video.period
    gaps = [max(1, round((b - a) / video.period)) * frame_ms for a, b in zip(stamps, stamps[1:])]
    if not gaps:
        return "one change, no pacing to read"
    median = sorted(gaps)[len(gaps) // 2]
    # a hold is measured against the burst's own pace, since an app that draws at 30 fps into a 60 fps recording changes every other frame and holds nothing
    limit = 1.5 * median
    held = [(burst[k + 1][0], g) for k, g in enumerate(gaps) if g > limit]
    text = f"a change every {median:.1f} ms at the median, the longest gap {max(gaps):.1f} ms, "
    if not held:
        return text + "no held frames"
    named = ", ".join(f"before F{f} ({g:.0f} ms, {round(g / frame_ms) - 1} frame{'s' if round(g / frame_ms) != 2 else ''} held)" for f, g in held[:HOLDS_NAMED])
    rest = f", and {len(held) - HOLDS_NAMED} more" if len(held) > HOLDS_NAMED else ""
    return text + f"{len(held)} hold{'s' if len(held) != 1 else ''} over {limit:.0f} ms: " + named + rest


def report(path: Path, out: Path, scale: float) -> None:
    video = media.Video(path)
    print(f"video {path}: {len(video.times)} frames, {video.width}x{video.height} px ({pt(video.width, scale)}x{pt(video.height, scale)} pt at {scale:g}x), {1000 * video.times[-1]:.0f} ms, a frame every {1000 * video.period:.1f} ms")
    cw, ch, moving = moving_pairs(video)
    bursts = bursts_of(video, moving)
    if not bursts:
        print("no motion past the noise floor, so no sheets were written")
        return
    still = len(video.times) - 1 - sum(len(b) for b in bursts)
    print(f"{len(bursts)} burst{'s' if len(bursts) != 1 else ''} of motion, {still} frames show no change past the noise floor")
    for number, burst in enumerate(bursts, 1):
        first, last = burst[0][0] - 1, burst[-1][0]
        span = 1000 * (video.times[last] - video.times[first])
        print(f"\nburst {number}: frames {first} to {last}, {1000 * video.times[first]:.0f} to {1000 * video.times[last]:.0f} ms ({span:.0f} ms), {len(burst)} frames changed")
        print(f"  pacing: {pacing(video, burst)}")
        for r, (x0, y0, x1, y1, _) in enumerate(regions_of(union(burst, cw * ch), cw, ch)[:4], 1):
            box = (x0 * CELL, y0 * CELL, min((x1 + 1) * CELL, video.width) - x0 * CELL, min((y1 + 1) * CELL, video.height) - y0 * CELL)
            own = [(f, sum(live[cy * cw + cx] for cy in range(y0, y1 + 1) for cx in range(x0, x1 + 1))) for f, _, live in burst]
            own = [(f, n) for f, n in own if n]
            if r > 2 or not own:
                print(f"  region {r}: {box_text(box, scale)}, no sheets, only the two largest regions get them, so take its frames with frame and a crop")
                continue
            overview, images = region_sheets(video, out, number, r, box, [own[0][0] - 1] + [f for f, _ in own], dict(own), scale)
            print(f"  region {r}: {box_text(box, scale)}" + (", key frames only, scaled" if overview else ""))
            for line in images:
                print(f"    {line}")
        print(f"  {'frame':<6} {'ms':>6} {'+ms':>5} {'changed px':>11}  (counted in {CELL} px cells)")
        before = video.times[first]
        for frame, changed, _ in burst:
            print(f"  F{frame:<5} {1000 * video.times[frame]:6.0f} {1000 * (video.times[frame] - before):5.0f} {changed:11}")
            before = video.times[frame]


def image_lines(written: list, spans: list) -> list:
    """A line per sheet written, naming the first and last moment its tiles show, so an agent opens the sheet it needs without opening the rest."""
    lines, k = [], 0
    for file, count, width, height in written:
        first, last = spans[k][0], spans[k + count - 1][1]
        shows = first if first == last else f"{first} to {last}"
        lines.append(f"image {file}: {shows}, {count} tile{'s' if count != 1 else ''}, {width}x{height}")
        k += count
    return lines


def region_sheets(video: media.Video, out: Path, burst: int, region: int, box: tuple, frames: list, weight: dict, scale: float) -> tuple:
    """The tagged frames and frame diffs of one region written, whether it was too big for full quality and got key frames instead, and a line per sheet."""
    pad = 8
    x, y, w, h = box
    x0, y0 = max(x - pad, 0), max(y - pad, 0)
    w, h = min(x + w + pad, video.width) - x0, min(y + h + pad, video.height) - y0
    factor = min(1.0, media.EDGE / w, math.sqrt(media.AREA * 0.8 / (w * h)))
    note = "EVERY FRAME WHERE THIS REGION CHANGED"
    overview = factor < 1
    picked = frames
    if overview:
        peak = max(weight.values())
        keys = [f for f in frames[1:] if weight.get(f, 0) >= peak / 3][:4]
        picked = sorted({frames[0], *keys, frames[-1]})
        rows = math.ceil(len(picked) / 2)
        factor = min((media.EDGE - draw.GAP) / 2 / w, ((media.AREA / media.EDGE - 140) / rows - 48) / h)
        note = "KEY FRAMES ONLY: THE ONE BEFORE, THOSE CHANGING A THIRD OF THE PEAK OR MORE, AND THE LAST. EVERY CHANGED FRAME IS IN THE TEXT TABLE"
    tw, th = max(1, round(w * factor)), max(1, round(h * factor))
    rgb = video.frames(picked, (x0, y0, w, h))
    quality = "FULL QUALITY, 1 IMAGE PX = 1 DEVICE PX" if factor == 1 else f"SCALED {factor:.2f}X FOR AN OVERVIEW, TAKE ONE FRAME WITH THE FRAME COMMAND TO JUDGE PIXELS"
    # the crop keeps a margin around the region so an edge that moved is never cut, and the header says so, since its numbers differ from the region line's
    where = f"X {x0} Y {y0} W {w} H {h} PX (PT {pt(x0, scale)},{pt(y0, scale)} {pt(w, scale)}X{pt(h, scale)}), THE REGION AND UP TO {pad} PX AROUND IT"
    tiles = []
    for k, frame in enumerate(picked):
        tile, _, _ = media.scaled(rgb[frame], w, h, factor)
        top = f"F{frame}   {1000 * video.times[frame]:.0f} MS"
        if k == 0:
            tiles.append((top, "BEFORE THE MOTION", GOLD, tile))
            continue
        before = picked[k - 1]
        tiles.append((top, f"+{1000 * (video.times[frame] - video.times[before]):.0f} MS  {media.changed_px(rgb[before], rgb[frame])} PX CHANGED", BLUE, tile))
    legend = "EACH TILE IS TAGGED: FRAME NUMBER AND MS FROM THE VIDEO'S START, THEN MS AND PIXELS CHANGED SINCE THE TILE BEFORE IT"
    written = draw.tagged_sheets(out, f"burst-{burst}-region-{region}-frames", f"FRAMES OF BURST {burst}, REGION {region}: {where}", [note, quality, legend], tiles, tw, th)
    lines = image_lines(written, [(f"F{f}", f"F{f}") for f in picked])
    light = media.is_light(rgb[picked[0]])
    diffs = []
    for a, b in zip(picked, picked[1:]):
        tile, _, _ = media.scaled(media.overlay(rgb[a], rgb[b], light), w, h, factor)
        diffs.append((f"F{a} TO F{b}", f"+{1000 * (video.times[b] - video.times[a]):.0f} MS  {media.changed_px(rgb[a], rgb[b])} PX CHANGED", TEAL, tile))
    notes = [
        "EACH TILE SHOWS WHAT CHANGED FROM ONE FRAME TO THE NEXT. RED: ONLY IN THE EARLIER FRAME. GREEN: ONLY IN THE LATER ONE. YELLOW: CHANGED IN BOTH. GREY: THE SAME",
        "EACH TILE IS TAGGED: THE TWO FRAMES, THEN MS AND PIXELS CHANGED BETWEEN THEM" + ("" if factor == 1 else f". SCALED {factor:.2f}X FOR AN OVERVIEW"),
    ]
    written = draw.tagged_sheets(out, f"burst-{burst}-region-{region}-diffs", f"FRAME DIFFS OF BURST {burst}, REGION {region}: {where}", notes, diffs, tw, th)
    lines += image_lines(written, [(f"F{a}", f"F{b}") for a, b in zip(picked, picked[1:])])
    return overview, lines


def frame(path: Path, index: int, out: Path, box, scale: float) -> None:
    video = media.Video(path)
    if not 0 <= index < len(video.times):
        raise media.SeeError(f"the video has frames 0 to {len(video.times) - 1}, so there is no frame {index}")
    region, clipped = media.clip(box or (0, 0, video.width, video.height), video.width, video.height)
    if clipped:
        print(f"the crop is clipped to x {region[0]} y {region[1]} w {region[2]} h {region[3]} to fit the frame")
    rgb = video.frames([index], region)[index]
    factor = min(1.0, media.EDGE / region[2], math.sqrt(media.AREA / (region[2] * region[3])))
    tile, tw, th = media.scaled(rgb, region[2], region[3], factor)
    quality = "full quality" if factor == 1 else f"scaled {factor:.2f}x"
    texts = [(f"FRAME {index} AT {1000 * video.times[index]:.0f} MS OF {path.name}, {box_text(region, scale).upper()}, {quality.upper()}", draw.WHITE)]
    width = max(tw, 400)
    head = draw.header_height(texts, width)
    canvas = draw.Canvas(width, head + th, draw.HEAD)
    draw.draw_header(canvas, texts)
    canvas.paste(0, head, tw, th, tile)
    canvas.save(out)
    print(f"image {out}: frame {index} at {1000 * video.times[index]:.0f} ms, {quality}, {canvas.width}x{canvas.height}")


def first_motion(video: media.Video, moving: list) -> int:
    """The first frame that changed past the noise floor, or 0 for a video that never moves."""
    return next((frame for frame, changed, _ in moving if changed >= FRAME_FLOOR), 0)


def compare(path_a: Path, path_b: Path, out: Path, box, scale: float) -> None:
    a, b = media.Video(path_a), media.Video(path_b)
    print(f"a {path_a}: {len(a.times)} frames, {a.width}x{a.height} px")
    print(f"b {path_b}: {len(b.times)} frames, {b.width}x{b.height} px")
    if (a.width, a.height) != (b.width, b.height):
        raise media.SeeError("the two recordings differ in size, so they cannot be laid side by side, record both at one size")
    cw, ch, moving_a = moving_pairs(a)
    _, _, moving_b = moving_pairs(b)
    start_a, start_b = first_motion(a, moving_a), first_motion(b, moving_b)
    print(f"a moves from F{start_a} and b from F{start_b}, lined up there")
    if box is None:
        cells = bytearray(cw * ch)
        for moving in (moving_a, moving_b):
            for _, changed, live in moving:
                if changed >= FRAME_FLOOR:
                    for k, c in enumerate(live):
                        if c:
                            cells[k] = 1
        found = regions_of(bytes(cells), cw, ch)
        if found:
            x0, y0, x1, y1 = min(r[0] for r in found), min(r[1] for r in found), max(r[2] for r in found), max(r[3] for r in found)
            box = (x0 * CELL, y0 * CELL, (x1 + 1) * CELL - x0 * CELL, (y1 + 1) * CELL - y0 * CELL)
        else:
            box = (0, 0, a.width, a.height)
    region, clipped = media.clip(box, a.width, a.height)
    print(f"compared over {box_text(region, scale)}" + (", clipped to the frame" if clipped else ""))
    base_a, base_b = max(start_a - 1, 0), max(start_b - 1, 0)
    rows = []
    for i in range(base_a, len(a.times)):
        t = a.times[i] - a.times[base_a]
        j = min(range(base_b, len(b.times)), key=lambda k: abs(b.times[k] - b.times[base_b] - t))
        if abs(b.times[j] - b.times[base_b] - t) > a.period:
            break
        rows.append((t, i, j))
    frames_a = a.frames([i for _, i, _ in rows], region)
    frames_b = b.frames([j for _, _, j in rows], region)
    counts = [media.changed_px(frames_a[i], frames_b[j]) for _, i, j in rows]
    print(f"  {'from start':>10}  {'a':<6} {'b':<6} px differ")
    again = next((k for k in range(len(rows)) if any(counts[:k]) and not any(counts[k:])), None)
    shown = len(rows) if again is None else min(len(rows), again + 3)
    for (t, i, j), n in zip(rows[:shown], counts[:shown]):
        print(f"  {f'+{1000 * t:.0f} ms':>10}  {f'F{i}':<6} {f'F{j}':<6} {n}")
    worst = max(range(len(rows)), key=lambda k: counts[k]) if rows else None
    if worst is not None and counts[worst]:
        print(f"the most apart at +{1000 * rows[worst][0]:.0f} ms, {counts[worst]} px differ")
    if again is not None:
        print(f"they match again from +{1000 * rows[again][0]:.0f} ms")
    elif any(counts):
        print("they still differ at the end of the shorter recording")
    else:
        print("they match all the way")
    pair_sheets(out, rows[:shown], counts, frames_a, frames_b, region, scale)


def pair_sheets(out: Path, rows: list, counts: list, frames_a: dict, frames_b: dict, region: tuple, scale: float) -> None:
    """Each moment as one tile, a beside b beside their overlay, tagged with the ms from the start, the frames and the pixels that differ."""
    _, _, w, h = region
    gap = 6
    factor = min(1.0, (media.EDGE - 2 * gap) / (3 * w), math.sqrt(media.AREA * 0.5 / (3 * w * h)))
    tw, th = max(1, round(w * factor)), max(1, round(h * factor))
    light = media.is_light(frames_a[rows[0][1]]) if rows else False
    tiles = []
    for (t, i, j), n in zip(rows, counts):
        parts = [media.scaled(part, w, h, factor)[0] for part in (frames_a[i], frames_b[j], media.overlay(frames_a[i], frames_b[j], light))]
        joined = bytearray(((3 * tw + 2 * gap) * th) * 3)
        for row in range(th):
            for p, part in enumerate(parts):
                at = (row * (3 * tw + 2 * gap) + p * (tw + gap)) * 3
                joined[at : at + tw * 3] = part[row * tw * 3 : (row + 1) * tw * 3]
        tiles.append((f"+{1000 * t:.0f} MS  A F{i}  B F{j}", f"{n} PX DIFFER", BLUE if n else TEAL, bytes(joined)))
    notes = [
        "EACH TILE IS ONE MOMENT, MS FROM THE FIRST MOTION: A ON THE LEFT, B IN THE MIDDLE, THEIR OVERLAY ON THE RIGHT, RED ONLY IN A, GREEN ONLY IN B, GREY THE SAME",
        "FULL QUALITY" if factor == 1 else f"SCALED {factor:.2f}X FOR AN OVERVIEW",
    ]
    written = draw.tagged_sheets(out, "compare", f"A AND B SIDE BY SIDE: {box_text(region, scale).upper()}", notes, tiles, 3 * tw + 2 * gap, th)
    for line in image_lines(written, [(f"+{1000 * t:.0f} ms", f"+{1000 * t:.0f} ms") for t, _, _ in rows]):
        print(line)
