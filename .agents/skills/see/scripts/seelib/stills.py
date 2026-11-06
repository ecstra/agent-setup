"""Two images compared: the changes boxed, each named moved, moved and changed, new, gone or changed in place, drawn as an overview and an image per change."""

import math
from pathlib import Path

from . import draw, media

THRESHOLD = 14  # a change counts past this many levels in any channel
FAINT = 4  # a box reaches over pixels this far apart, so a moved box that also changed shade stays one box
REACH = 8  # a move is looked for up to this many px each way
CYAN = (0, 220, 230)


def pt(value: float, scale: float) -> str:
    return f"{value / scale:g}"


def differing_rows(a: bytes, b: bytes, width: int, height: int, wa: int, wb: int, limit: int) -> dict:
    """Per row, the columns where any channel differs past the limit."""
    rows = {}
    for y in range(height):
        ra = a[y * wa * 3 : (y * wa + width) * 3]
        rb = b[y * wb * 3 : (y * wb + width) * 3]
        if ra == rb:
            continue
        cols = [x for x in range(width) if max(abs(ra[3 * x] - rb[3 * x]), abs(ra[3 * x + 1] - rb[3 * x + 1]), abs(ra[3 * x + 2] - rb[3 * x + 2])) > limit]
        if cols:
            rows[y] = cols
    return rows


def boxes_of(rows: dict, row_gap: int = 12, col_gap: int = 24) -> list:
    """Bands of rows a few apart, each cut into boxes of columns a few apart."""
    bands = []
    for y in sorted(rows):
        if bands and y <= bands[-1][1] + row_gap:
            bands[-1][1] = y
        else:
            bands.append([y, y])
    found = []
    for y0, y1 in bands:
        groups = []
        for x in sorted({x for y in range(y0, y1 + 1) for x in rows.get(y, ())}):
            if groups and x <= groups[-1][1] + col_gap:
                groups[-1][1] = x
            else:
                groups.append([x, x])
        found += [(x0, y0, x1 - x0 + 1, y1 - y0 + 1) for x0, x1 in groups]
    return found


def mismatches(a: bytes, b: bytes, wa: int, wb: int, box: tuple, dx: int, dy: int, limit: int) -> int:
    """How many pixels of the box in a differ from b moved by dx, dy, stopping once past the limit."""
    x, y, w, h = box
    count = 0
    for row in range(y, y + h):
        ra = a[(row * wa + x) * 3 : (row * wa + x + w) * 3]
        rb = b[((row + dy) * wb + x + dx) * 3 : ((row + dy) * wb + x + dx + w) * 3]
        if ra == rb:
            continue
        count += sum(1 for k in range(0, len(ra), 3) if max(abs(ra[k] - rb[k]), abs(ra[k + 1] - rb[k + 1]), abs(ra[k + 2] - rb[k + 2])) > THRESHOLD)
        if count > limit:
            break
    return count


def best_shift(a: bytes, b: bytes, wa: int, wb: int, width: int, height: int, box: tuple) -> tuple:
    """The offset of b that lines the box up best, what differed before it and what still differs after."""
    x, y, w, h = box
    if x - REACH < 0 or y - REACH < 0 or x + w + REACH > width or y + h + REACH > height:
        return (0, 0), 0, 0
    base = mismatches(a, b, wa, wb, box, 0, 0, 10**9)
    best = ((0, 0), base)
    for dy in range(-REACH, REACH + 1):
        n = mismatches(a, b, wa, wb, box, 0, dy, best[1])
        if n < best[1]:
            best = ((0, dy), n)
    dy = best[0][1]
    # a sideways move must explain half of what is left, so a horizontal edge, which lines up at any dx, keeps dx 0
    for dx in range(-REACH, REACH + 1):
        n = mismatches(a, b, wa, wb, box, dx, dy, best[1])
        if dx and n < best[1] * 0.5:
            best = ((dx, dy), n)
    return best[0], base, best[1]


def ink_share(rgb: bytes, width: int, box: tuple, ground: bytes) -> float:
    """The share of the box's pixels that differ from the ground."""
    x, y, w, h = box
    count = sum(1 for row in range(y, y + h) for col in range(x, x + w) if media.apart(rgb[(row * width + col) * 3 : (row * width + col) * 3 + 3], ground) > THRESHOLD)
    return count / (w * h)


def colour_left(a: bytes, b: bytes, wa: int, wb: int, box: tuple, dx: int, dy: int) -> int:
    x, y, w, h = box
    worst = 0
    for row in range(y, y + h):
        ra = a[(row * wa + x) * 3 : (row * wa + x + w) * 3]
        rb = b[((row + dy) * wb + x + dx) * 3 : ((row + dy) * wb + x + dx + w) * 3]
        if ra != rb:
            worst = max(worst, max(abs(p - q) for p, q in zip(ra, rb)))
    return worst


def ground_of(rgb: bytes) -> bytes:
    tally = {}
    for i in range(0, len(rgb) - 2, 3 * 31):
        c = rgb[i : i + 3]
        tally[c] = tally.get(c, 0) + 1
    return max(tally, key=tally.get)


def name_change(a: bytes, b: bytes, wa: int, wb: int, width: int, height: int, box: tuple, ground: bytes, scale: float) -> tuple:
    """What a box's change is, in words, and the offset of b that lines it up."""
    if ink_share(a, wa, box, ground) < 0.02 and ink_share(b, wb, box, ground) >= 0.02:
        return "new in b, nothing was there in a", 0, 0
    if ink_share(b, wb, box, ground) < 0.02 and ink_share(a, wa, box, ground) >= 0.02:
        return "gone from b, it was there in a", 0, 0
    (dx, dy), before, after = best_shift(a, b, wa, wb, width, height, box)
    moves = []
    if dx:
        moves.append(f"{'right' if dx > 0 else 'left'} {abs(dx)} px ({pt(abs(dx), scale)} pt)")
    if dy:
        moves.append(f"{'down' if dy > 0 else 'up'} {abs(dy)} px ({pt(abs(dy), scale)} pt)")
    if moves and after <= before * 0.05:
        words = "moved " + " and ".join(moves) + ", the same shape once aligned"
        shade = colour_left(a, b, wa, wb, box, dx, dy)
        return words + (f", colour off by up to {shade} of 255" if shade > 2 else ""), dx, dy
    if moves and after <= before * 0.25:
        return "moved " + " and ".join(moves) + f" and changed, {after} px still differ once aligned", dx, dy
    return "changed in place", 0, 0


def diff(path_a: Path, path_b: Path, out: Path, scale: float) -> None:
    wa, ha, a = media.image(path_a)
    wb, hb, b = media.image(path_b)
    width, height = min(wa, wb), min(ha, hb)
    print(f"a {path_a}: {wa}x{ha} px")
    print(f"b {path_b}: {wb}x{hb} px")
    if (wa, ha) != (wb, hb):
        print(f"the sizes differ, so only the top left {width}x{height} is compared")
    counted = differing_rows(a, b, width, height, wa, wb, THRESHOLD)
    total = sum(len(c) for c in counted.values())
    if not total:
        print(f"the images are the same past {THRESHOLD} of 255")
        return
    light = media.is_light(a)
    print(f"{total} of {width * height} px differ past {THRESHOLD} of 255, on a {'light' if light else 'dark'} background")
    found = []
    for x, y, w, h in boxes_of(differing_rows(a, b, width, height, wa, wb, FAINT)):
        count = sum(1 for row in range(y, y + h) for col in counted.get(row, ()) if x <= col < x + w)
        if count:
            found.append((x, y, w, h, count))
    found.sort(key=lambda f: -f[4])
    ground = ground_of(a)
    results = []
    for n, (x, y, w, h, count) in enumerate(found[:12], 1):
        words, dx, dy = name_change(a, b, wa, wb, width, height, (x, y, w, h), ground, scale)
        results.append((n, (x, y, w, h), count, words, dx, dy))
        print(f"#{n}: x {x} y {y} w {w} h {h} px (x {pt(x, scale)} y {pt(y, scale)} w {pt(w, scale)} h {pt(h, scale)} pt), {count} px differ: {words}")
    if len(found) > 12:
        print(f"{len(found) - 12} smaller changes are not listed, compare a region of them with zoom")
    overview(a, b, wa, wb, width, height, results, light, out, path_a, path_b)
    for result in results:
        change_image(a, b, wa, wb, width, height, result, light, out, scale)


def onion(a: bytes, b: bytes, wa: int, wb: int, box: tuple, dx: int, dy: int, light: bool) -> bytes:
    x, y, w, h = box
    part_a = media.crop(a, wa, box)
    part_b = media.crop(b, wb, (x + dx, y + dy, w, h))
    return media.overlay(part_a, part_b, light)


def overview(a, b, wa, wb, width, height, results, light, out, path_a, path_b):
    whole = onion(a, b, wa, wb, (0, 0, width, height), 0, 0, light)
    factor = min(1.0, media.EDGE / width, math.sqrt(media.AREA * 0.85 / (width * height)))
    tile, tw, th = media.scaled(whole, width, height, factor)
    texts = [
        (f"DIFF OVERVIEW: A = {path_a.name}, B = {path_b.name}", draw.WHITE),
        ("RED: ONLY IN A. GREEN: ONLY IN B. YELLOW: IN BOTH, CHANGED. GREY: THE SAME. CYAN BOXES: THE NUMBERED CHANGES, ONE IMAGE EACH", draw.DIM),
        (("FULL QUALITY" if factor == 1 else f"SCALED {factor:.2f}X TO FIT") + ". THIS SHOWS WHERE. JUDGE WHAT ON THE NUMBERED CHANGE IMAGES", (255, 200, 120)),
    ]
    head = draw.header_height(texts, tw)
    canvas = draw.Canvas(tw, head + th, draw.HEAD)
    draw.draw_header(canvas, texts)
    canvas.paste(0, head, tw, th, tile)
    label_h = draw.text_size("X")[1]
    for n, (x, y, w, h), _, _, _, _ in results:
        bx, by = int(x * factor), head + int(y * factor)
        canvas.outline(bx - 3, by - 3, int(w * factor) + 6, int(h * factor) + 6, CYAN, 2)
        tag_y = by - 3 - label_h if by - 3 - label_h > head else by + int(h * factor) + 4
        canvas.text(bx - 3, tag_y, f"#{n}", 2, (0, 0, 0), CYAN)
    canvas.save(out / "diff-overview.png")
    print(f"image {out / 'diff-overview.png'}: where each change is, {canvas.width}x{canvas.height}")


def change_image(a, b, wa, wb, width, height, result, light, out, scale):
    """One change as A, B, their overlay and, where it moved, the overlay once B is lined up, as large as the budget allows."""
    n, (x, y, w, h), count, words, dx, dy = result
    pad = 6
    x0, y0 = max(x - pad, 0, -dx), max(y - pad, 0, -dy)
    x1, y1 = min(x + w + pad, width, wb - dx), min(y + h + pad, height, height - dy)
    box = (x0, y0, x1 - x0, y1 - y0)
    _, _, w0, h0 = box
    parts = [("A", media.crop(a, wa, box)), ("B", media.crop(b, wb, box)), ("OVERLAY", onion(a, b, wa, wb, box, 0, 0, light))]
    if dx or dy:
        parts.append((f"B LINED UP, MOVED {-dx},{-dy}", onion(a, b, wa, wb, box, dx, dy, light)))
    label_h = draw.text_size("X")[1]
    cols = max(1, min(len(parts), (media.EDGE + draw.GAP) // (w0 + draw.GAP)))
    rows = math.ceil(len(parts) / cols)
    factor = max(1, min(8, (media.EDGE + draw.GAP) // cols // (w0 + draw.GAP), (1300 // rows - 2 * label_h) // max(h0, 1)))
    if factor > 1 and (w0 * factor) * (h0 * factor) * len(parts) > media.AREA:
        factor = 1
    if w0 * h0 * len(parts) * factor * factor > media.AREA:
        factor = math.sqrt(media.AREA * 0.85 / (w0 * h0 * len(parts)))
    tw, th = max(1, round(w0 * factor)), max(1, round(h0 * factor))
    size = f"ZOOMED {factor:g}X, NEAREST NEIGHBOUR" if factor > 1 else ("FULL QUALITY" if factor == 1 else f"SCALED {factor:.2f}X, ZOOM IN TO JUDGE PIXELS")
    texts = [
        (f"CHANGE #{n}: {words.upper()}", draw.WHITE),
        (f"X {x0} Y {y0} W {w0} H {h0} PX (PT {pt(x0, scale)},{pt(y0, scale)} {pt(w0, scale)}X{pt(h0, scale)}), {size}, {count} PX DIFFER", draw.DIM),
        ("OVERLAY: RED ONLY IN A, GREEN ONLY IN B, YELLOW CHANGED IN BOTH, GREY THE SAME", draw.DIM),
    ]
    width_out = max(cols * (tw + draw.GAP) - draw.GAP, 600)
    head = draw.header_height(texts, width_out)
    canvas = draw.Canvas(width_out, head + rows * (th + label_h + draw.GAP), (60, 60, 66))
    draw.draw_header(canvas, texts)
    for k, (title, rgb) in enumerate(parts):
        tile, _, _ = media.scaled(rgb, w0, h0, factor)
        cx, cy = (k % cols) * (tw + draw.GAP), head + (k // cols) * (th + label_h + draw.GAP)
        canvas.text(cx, cy, title, 2, (0, 0, 0), (230, 230, 235))
        canvas.paste(cx, cy + label_h, tw, th, tile)
    path = out / f"diff-change-{n}.png"
    canvas.save(path)
    print(f"image {path}: change #{n}, {canvas.width}x{canvas.height}")
