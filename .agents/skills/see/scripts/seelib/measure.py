"""An image measured the way a design tool does: elements, their sizes, the items inside and the gaps, drawn as a redline, and a region at the pixel with its edges as numbers."""

from pathlib import Path

from . import draw, media

INK = 8  # a white card on a near white page is 11 levels off, and a screenshot carries no noise, so 8 finds both
MERGE = 14  # pieces this close become one item, the letters and words of a label, about 7 pt at 2x
PURPLE, CYAN, MAGENTA, ORANGE, GREEN, RED = (124, 77, 255), (0, 170, 230), (230, 40, 200), (255, 150, 0), (40, 200, 90), (230, 40, 40)


def far(c: bytes, ref: bytes, limit: int = INK) -> bool:
    return max(abs(c[0] - ref[0]), abs(c[1] - ref[1]), abs(c[2] - ref[2])) > limit


def pt(value: float, scale: float) -> str:
    return f"{value / scale:g}"


def components(mask: bytearray, w: int, h: int, box=None) -> list:
    """8 connected pieces of the mask as [x0, y0, x1, y1, count], within the box if given."""
    bx0, by0, bx1, by1 = box or (0, 0, w - 1, h - 1)
    seen = bytearray(w * h)
    found = []
    for y in range(by0, by1 + 1):
        for x in range(bx0, bx1 + 1):
            start = y * w + x
            if not mask[start] or seen[start]:
                continue
            seen[start] = 1
            stack, count = [start], 0
            x0 = x1 = x
            y0 = y1 = y
            while stack:
                at = stack.pop()
                count += 1
                cx, cy = at % w, at // w
                x0, x1, y0, y1 = min(x0, cx), max(x1, cx), min(y0, cy), max(y1, cy)
                for ny in (cy - 1, cy, cy + 1):
                    if by0 <= ny <= by1:
                        for nx in (cx - 1, cx, cx + 1):
                            if bx0 <= nx <= bx1 and mask[ny * w + nx] and not seen[ny * w + nx]:
                                seen[ny * w + nx] = 1
                                stack.append(ny * w + nx)
            found.append([x0, y0, x1, y1, count])
    return found


def inside(a: list, b: list) -> bool:
    return b[0] <= a[0] and b[1] <= a[1] and a[2] <= b[2] and a[3] <= b[3] and a[:4] != b[:4]


def hollow(b: list) -> bool:
    """A ring, whose ink covers little of its box, so what sits inside it stays apart from it."""
    return b[4] < 0.12 * (b[2] - b[0] + 1) * (b[3] - b[1] + 1) and b[2] - b[0] > 40 and b[3] - b[1] > 20


def merged(boxes: list, gap: int = MERGE) -> list:
    boxes = [list(b) for b in boxes]
    joined = True
    while joined:
        joined = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                if (inside(a, b) and hollow(b)) or (inside(b, a) and hollow(a)):
                    continue
                if a[0] - gap <= b[2] and b[0] - gap <= a[2] and a[1] - gap <= b[3] and b[1] - gap <= a[3]:
                    boxes[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]), a[4] + b[4]]
                    del boxes[j]
                    joined = True
                    break
            if joined:
                break
    return boxes


def commonest(crop: bytes, w: int, points) -> bytes:
    tally = {}
    for x, y in points:
        c = crop[(y * w + x) * 3 : (y * w + x) * 3 + 3]
        tally[c] = tally.get(c, 0) + 1
    return max(tally, key=tally.get)


def fill_of(crop: bytes, w: int, box: list, background: bytes):
    """An element's fill, the commonest exact colour of its commonest group of 8 levels a channel, since a rendered fill wanders by a level or two, or None where it has none."""
    x0, y0, x1, y1 = box[:4]
    groups, exact = {}, {}
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            c = crop[(y * w + x) * 3 : (y * w + x) * 3 + 3]
            key = (c[0] >> 3, c[1] >> 3, c[2] >> 3)
            groups[key] = groups.get(key, 0) + 1
            exact[c] = exact.get(c, 0) + 1
    top = max(groups, key=groups.get)
    fill = max((c for c in exact if (c[0] >> 3, c[1] >> 3, c[2] >> 3) == top), key=exact.get)
    if groups[top] < 0.4 * (x1 - x0 + 1) * (y1 - y0 + 1) or not far(fill, background):
        return None
    return fill


def items_in(crop: bytes, w: int, box: list, fill: bytes) -> list:
    """What a filled element holds: what differs from its fill and is not reached from its edge, so its rounded corners stay out."""
    x0, y0, x1, y1 = box[:4]
    other = bytearray(w * (y1 + 1))
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if far(crop[(y * w + x) * 3 : (y * w + x) * 3 + 3], fill):
                other[y * w + x] = 1
    edge = [y * w + x for y in (y0, y1) for x in range(x0, x1 + 1)] + [y * w + x for x in (x0, x1) for y in range(y0, y1 + 1)]
    stack = [at for at in edge if other[at]]
    for at in stack:
        other[at] = 0
    while stack:
        at = stack.pop()
        cx, cy = at % w, at // w
        for ny in (cy - 1, cy, cy + 1):
            for nx in (cx - 1, cx, cx + 1):
                if x0 <= nx <= x1 and y0 <= ny <= y1 and other[ny * w + nx]:
                    other[ny * w + nx] = 0
                    stack.append(ny * w + nx)
    pieces = [p for p in components(other, w, y1 + 1, (x0, y0, x1, y1)) if p[4] >= 6]
    return merged(pieces)


def arranged(items: list) -> tuple:
    """The items in reading order and how they sit: a row when each overlaps the next in height, a column when each overlaps the next in width, else free."""
    if len(items) < 2:
        return items, "row"
    by_x = sorted(items, key=lambda b: b[0])
    if all(a[1] <= b[3] and b[1] <= a[3] and a[2] < b[0] for a, b in zip(by_x, by_x[1:])):
        return by_x, "row"
    by_y = sorted(items, key=lambda b: b[1])
    if all(a[0] <= b[2] and b[0] <= a[2] and a[3] < b[1] for a, b in zip(by_y, by_y[1:])):
        return by_y, "column"
    return by_y, "free"


def soft_box(crop: bytes, w: int, h: int, box: list, faint: int = 3, reach: int = 3) -> tuple:
    """The box grown over its antialiased edge, against the commonest colour just outside it, so text on a card is measured against the card."""
    x0, y0, x1, y1 = box[:4]
    ring = [(x, y) for x in range(max(x0 - reach - 1, 0), min(x1 + reach + 2, w)) for y in (max(y0 - reach - 1, 0), min(y1 + reach + 1, h - 1))]
    ring += [(x, y) for y in range(max(y0 - reach - 1, 0), min(y1 + reach + 2, h)) for x in (max(x0 - reach - 1, 0), min(x1 + reach + 1, w - 1))]
    ground = commonest(crop, w, ring)

    def any_far(points) -> bool:
        return any(far(crop[(y * w + x) * 3 : (y * w + x) * 3 + 3], ground, faint) for x, y in points)

    for _ in range(reach):
        if y0 > 0 and any_far((x, y0 - 1) for x in range(x0, x1 + 1)):
            y0 -= 1
        if y1 < h - 1 and any_far((x, y1 + 1) for x in range(x0, x1 + 1)):
            y1 += 1
        if x0 > 0 and any_far((x0 - 1, y) for y in range(y0, y1 + 1)):
            x0 -= 1
        if x1 < w - 1 and any_far((x1 + 1, y) for y in range(y0, y1 + 1)):
            x1 += 1
    return x0, y0, x1, y1


def describe(crop: bytes, w: int, box: list, fill, items: list, how: str, background: bytes, origin: tuple, indent: str, name: str) -> None:
    """The items of an element, their padding and the gaps along the way they lie, and one level further into an item with a fill of its own."""
    x, y = origin
    for k, it in enumerate(items, 1):
        print(f"{indent}{name}.{k}: x {x + it[0]} y {y + it[1]}, {it[2] - it[0] + 1} x {it[3] - it[1] + 1} px")
    if not items:
        return
    if how == "row":
        gaps = [b[0] - a[2] - 1 for a, b in zip(items, items[1:])]
        centre = (box[1] + box[3]) / 2
        print(f"{indent}in a row: padding left {items[0][0] - box[0]}, right {box[2] - items[-1][2]}" + (f", gaps {', '.join(map(str, gaps))}" if gaps else "") + f"; tops {[it[1] - box[1] for it in items]} from the top, bottoms {[box[3] - it[3] for it in items]} from the bottom")
        print(f"{indent}off the vertical centre: " + ", ".join(f"{(it[1] + it[3]) / 2 - centre:+.1f}" for it in items) + ", where a text box holds its descenders, so text sits a little high of its box's centre")
    elif how == "column":
        gaps = [b[1] - a[3] - 1 for a, b in zip(items, items[1:])]
        print(f"{indent}in a column: padding top {items[0][1] - box[1]}, bottom {box[3] - items[-1][3]}" + (f", gaps {', '.join(map(str, gaps))}" if gaps else "") + f"; lefts {[it[0] - box[0] for it in items]} from the left, rights {[box[2] - it[2] for it in items]} from the right")
    else:
        for k, it in enumerate(items, 1):
            print(f"{indent}{name}.{k} sits {it[0] - box[0]} from the left, {it[1] - box[1]} from the top, {box[2] - it[2]} from the right, {box[3] - it[3]} from the bottom")
    if name.count(".") >= 1:
        return
    for k, it in enumerate(items, 1):
        inner_fill = fill_of(crop, w, it, background)
        # only an item whose fill differs from its parent's is a container of its own, never a word on the parent's fill
        if inner_fill and (fill is None or far(inner_fill, fill)):
            inner, inner_how = arranged(items_in(crop, w, it, inner_fill))
            if inner:
                print(f"{indent}{name}.{k} has the fill #{inner_fill.hex()} and holds")
                describe(crop, w, it, inner_fill, inner, inner_how, background, origin, indent + "   ", f"{name}.{k}")


def redline(path: Path, out: Path, box, scale: float) -> None:
    iw, ih, rgb = media.image(path)
    region, clipped = media.clip(box or (0, 0, iw, ih), iw, ih)
    x, y, w, h = region
    if clipped:
        print(f"the region is clipped to x {x} y {y} w {w} h {h} to fit the image")
    crop = media.crop(rgb, iw, region)
    background = commonest(crop, w, [(xx, yy) for yy in (0, h - 1) for xx in range(w)] + [(xx, yy) for xx in (0, w - 1) for yy in range(h)])
    mask = bytearray(w * h)
    for i in range(w * h):
        if far(crop[3 * i : 3 * i + 3], background):
            mask[i] = 1
    boxes = merged([p for p in components(mask, w, h) if p[4] >= 12])
    tops = sorted((b for b in boxes if not any(inside(b, o) for o in boxes)), key=lambda b: (b[1] // 20, b[0]))
    print(f"{path}: region x {x} y {y} w {w} h {h} px, background #{background.hex()}, all numbers in device px, pt = px / {scale:g}")
    if not tops:
        print("nothing stands out from the background in the region")
    elements = []
    for n, el in enumerate(tops, 1):
        fill = fill_of(crop, w, el, background)
        items = items_in(crop, w, el, fill) if fill else sorted((b for b in boxes if inside(b, el)), key=lambda b: b[0])
        items, how = arranged(items)
        ew, eh = el[2] - el[0] + 1, el[3] - el[1] + 1
        sx0, sy0, sx1, sy1 = soft_box(crop, w, h, el)
        cut = el[0] == 0 or el[1] == 0 or el[2] == w - 1 or el[3] == h - 1
        print(
            f"E{n}: x {x + el[0]} y {y + el[1]}, {ew} x {eh} px ({pt(ew, scale)} x {pt(eh, scale)} pt) solid, {sx1 - sx0 + 1} x {sy1 - sy0 + 1} px with its soft edge" + (f", fill #{fill.hex()}" if fill else ", no fill, an outline or bare ink") + (", cut by the region's edge, so its size is not its own" if cut else "")
        )
        describe(crop, w, el, fill, items, how, background, (x, y), "   ", f"E{n}")
        elements.append((n, el, items, how))
    gaps = []
    for n, el, _, _ in elements:
        across = [(o[0] - el[2] - 1, m, o) for m, o, _, _ in elements if o[0] > el[2] and o[1] <= el[3] and el[1] <= o[3]]
        down = [(o[1] - el[3] - 1, m, o) for m, o, _, _ in elements if o[1] > el[3] and o[0] <= el[2] and el[0] <= o[2]]
        if across:
            g, m, o = min(across)
            gaps.append(("across", n, m, g, el, o))
            print(f"gap E{n} to E{m}, across: {g} px ({pt(g, scale)} pt)")
        if down:
            g, m, o = min(down)
            gaps.append(("down", n, m, g, el, o))
            print(f"gap E{n} to E{m}, down: {g} px ({pt(g, scale)} pt)")
    for side, k in (("tops", 1), ("bottoms", 3)):
        lined = {}
        for n, el, _, _ in elements:
            lined.setdefault(el[k], []).append(f"E{n}")
        for at, names in lined.items():
            if len(names) > 1:
                print(f"aligned {side}: {', '.join(names)} at y {y + at}")
    draw_redline(crop, w, h, elements, gaps, out, path, region, scale)


def draw_redline(crop, w, h, elements, gaps, out, path, region, scale):
    zoom = 2 if w * 2 + 60 <= media.EDGE and (w * 2 + 60) * (h * 2 + 160) <= media.AREA else 1
    factor = zoom if zoom > 1 else min(1.0, (media.EDGE - 60) / w, ((media.AREA / (w + 60)) - 160) / h)
    tile, tw, th = media.scaled(crop, w, h, factor)
    margin = 30
    texts = [
        (f"REDLINE OF {path.name}, REGION X {region[0]} Y {region[1]} W {w} H {h}, SHOWN AT {factor:.2g}X. NUMBERS ARE DEVICE PX, PT = PX / {scale:g}", draw.WHITE),
        ("MAGENTA: ELEMENTS, NUMBERED. PURPLE: WIDTH. CYAN: HEIGHT. ORANGE: ITEMS INSIDE. GREEN: PADDING AND GAPS INSIDE. RED: GAPS BETWEEN ELEMENTS", draw.DIM),
    ]
    width = tw + 2 * margin
    head = draw.header_height(texts, width)
    canvas = draw.Canvas(width, head + th + 2 * margin, (40, 40, 44))
    draw.draw_header(canvas, texts)
    ox, oy = margin, head + margin
    canvas.paste(ox, oy, tw, th, tile)
    placed = []

    def s(value: float) -> int:
        return int(value * factor)

    def pill(cx: int, cy: int, text: str, colour: tuple) -> None:
        """A label centred on a point, moved down a step at a time past any label already drawn, so no two overlap."""
        lw, lh = draw.text_size(text)
        lx, ly = cx - lw // 2, cy - lh // 2
        for _ in range(8):
            if not any(lx < px + pw and px < lx + lw + 4 and ly < py + ph and py < ly + lh for px, py, pw, ph in placed):
                break
            ly += lh + 2
        placed.append((lx, ly, lw + 4, lh))
        canvas.text(lx, ly, text, 2, draw.WHITE, colour)

    for n, el, items, how in elements:
        x0, y0, x1, y1 = ox + s(el[0]), oy + s(el[1]), ox + s(el[2] + 1), oy + s(el[3] + 1)
        canvas.outline(x0, y0, x1 - x0, y1 - y0, MAGENTA, 1)
        canvas.text(x0, y0 - 18 if y0 - 18 > head else y1 + 2, f"E{n}", 2, draw.WHITE, MAGENTA)
        mid = (y0 + y1) // 2
        canvas.rect(x0, mid, x1 - x0, 1, PURPLE)
        canvas.rect(x0, mid - 5, 1, 11, PURPLE)
        canvas.rect(x1 - 1, mid - 5, 1, 11, PURPLE)
        pill((x0 + x1) // 2, y0 + 12, f"{el[2] - el[0] + 1}", PURPLE)
        canvas.rect(x1 + 6, y0, 1, y1 - y0, CYAN)
        canvas.rect(x1 + 1, y0, 11, 1, CYAN)
        canvas.rect(x1 + 1, y1 - 1, 11, 1, CYAN)
        pill(x1 + 6, (y0 + y1) // 2, f"{el[3] - el[1] + 1}", CYAN)
        for it in items:
            canvas.outline(ox + s(it[0]), oy + s(it[1]), max(1, s(it[2] - it[0] + 1)), max(1, s(it[3] - it[1] + 1)), ORANGE, 1)
        if items and how == "row":
            edges = [el[0] - 1] + [v for it in items for v in (it[0], it[2])] + [el[2] + 1]
            for k in range(0, len(edges), 2):
                a, b = edges[k], edges[k + 1]
                if b - a - 1 > 0:
                    row = oy + s((items[min(k // 2, len(items) - 1)][1] + items[min(k // 2, len(items) - 1)][3]) / 2) + 14
                    canvas.rect(ox + s(a + 1), row, s(b - a - 1), 1, GREEN)
                    pill(ox + s((a + b) / 2), row + 10, f"{b - a - 1}", GREEN)
        elif items and how == "column":
            edges = [el[1] - 1] + [v for it in items for v in (it[1], it[3])] + [el[3] + 1]
            col = ox + s(min(it[0] for it in items)) - 12
            for k in range(0, len(edges), 2):
                a, b = edges[k], edges[k + 1]
                if b - a - 1 > 0:
                    canvas.rect(col, oy + s(a + 1), 1, s(b - a - 1), GREEN)
                    pill(col - 20, oy + s((a + b) / 2), f"{b - a - 1}", GREEN)
    for way, _, _, g, a, b in gaps:
        if way == "across":
            row = oy + s(max(a[1], b[1]) + 4)
            canvas.rect(ox + s(a[2] + 1), row, max(1, s(g)), 2, RED)
            pill(ox + s(a[2] + 1 + g / 2), row + 14, f"{g}", RED)
        else:
            col = ox + s(max(a[0], b[0]) + 4)
            canvas.rect(col, oy + s(a[3] + 1), 2, max(1, s(g)), RED)
            pill(col + 24, oy + s(a[3] + 1 + g / 2), f"{g}", RED)
    canvas.save(out)
    print(f"image {out}: the redline, {canvas.width}x{canvas.height}")


def ink_of(crop: bytes, w: int, h: int) -> tuple:
    """The background is the commonest colour on the region's border, and ink what differs from it by more than 24, with the ink's box and colours."""
    ground = commonest(crop, w, [(x, y) for y in (0, h - 1) for x in range(w)] + [(x, y) for x in (0, w - 1) for y in range(h)])
    x0 = y0 = 10**9
    x1 = y1 = -1
    colours = {}
    for y in range(h):
        for x in range(w):
            c = crop[(y * w + x) * 3 : (y * w + x) * 3 + 3]
            if far(c, ground, 24):
                x0, x1, y0, y1 = min(x0, x), max(x1, x), min(y0, y), max(y1, y)
                colours[c] = colours.get(c, 0) + 1
    return ground, ((x0, y0, x1, y1) if x1 >= 0 else None), colours


def edge_lines(crop: bytes, w: int, h: int, region: tuple, ink: tuple, ground: bytes, main: bytes) -> list:
    """The coverage of the ink's left and top edges, each read along the line nearest the ink's middle that reaches the edge, and where each is half covered."""
    x, y = region[0], region[1]
    x0, y0, x1, y1 = ink
    span = max(abs(main[k] - ground[k]) for k in range(3)) or 1

    def cover(col: int, row: int) -> float:
        c = crop[(row * w + col) * 3 :][:3]
        return min(max(abs(c[k] - ground[k]) for k in range(3)) / span, 1.0)

    lines = []
    for name, across, lo, first, last in (("left edge", "y", x0, y0, y1), ("top edge", "x", y0, x0, x1)):
        # text has gaps between its lines and its letters, so the middle line can miss the ink and read the edge as empty
        middle = (first + last) // 2
        along = sorted(range(first, last + 1), key=lambda k: abs(k - middle))
        reach = (lambda k: cover(lo, k)) if across == "y" else (lambda k: cover(k, lo))
        at = next((k for k in along if reach(k) >= 0.5), max(along, key=reach))
        values = []
        for i in range(max(0, lo - 3), min(lo + 3, w if across == "y" else h)):
            values.append((i + (x if across == "y" else y), cover(i, at) if across == "y" else cover(at, i)))
        half = next((i for i, cover in values if cover >= 0.5), None)
        lines.append(f"  {name} along {across} {at + (y if across == 'y' else x)}: coverage " + " ".join(f"{i}:{cover:.2f}" for i, cover in values) + (f", half covered at {half}" if half is not None else ""))
    return lines


def zoom(out: Path, box: tuple, paths: list, scale: float) -> None:
    loaded = [media.image(p) for p in paths]
    width, height = min(w for w, _, _ in loaded), min(h for _, h, _ in loaded)
    region, clipped = media.clip(box, width, height)
    x, y, w, h = region
    if clipped:
        print(f"the region is clipped to x {x} y {y} w {w} h {h} to fit the image")
    ruler = 46
    factor = max(1, min(16, (media.EDGE // len(paths) - ruler - 16) // w, (media.EDGE - ruler - 160) // h))
    while factor > 1 and (len(paths) * (w * factor + ruler + 16)) * (h * factor + ruler + 160) > media.AREA:
        factor -= 1
    panel_w, panel_h = w * factor + ruler, h * factor + ruler
    texts = [
        (f"ZOOM: X {x} Y {y} W {w} H {h} DEVICE PX AT {factor}X, NEAREST NEIGHBOUR. PT = PX / {scale:g}", draw.WHITE),
        ("RULERS: DEVICE PX OF THE WHOLE IMAGE. THIN LINES: EVERY PIXEL. DARK LINES: EVERY 10 PX", draw.DIM),
        ("PANELS LEFT TO RIGHT: " + ", ".join(p.name for p in paths) + ". EDGES, SIZES AND COLOURS ARE IN THE TEXT REPORT", draw.DIM),
    ]
    width_out = panel_w * len(paths) + 16 * (len(paths) - 1)
    head = draw.header_height(texts, width_out)
    canvas = draw.Canvas(width_out, head + panel_h + 8, (250, 250, 252))
    draw.draw_header(canvas, texts)
    inks = []
    for p, (path, (iw, _, rgb)) in enumerate(zip(paths, loaded)):
        crop = media.crop(rgb, iw, region)
        tile, tw, th = media.scaled(crop, w, h, factor)
        ox, oy = p * (panel_w + 16), head
        canvas.paste(ox + ruler, oy + ruler, tw, th, tile)
        canvas.text(ox, oy, path.name[:12], 1, (0, 0, 0), None)
        for i in range(w + 1):
            gx, major = ox + ruler + i * factor, (x + i) % 10 == 0
            if factor >= 6 or major:
                canvas.rect(gx, oy + ruler, 1, th, (0, 0, 0) if major else (150, 150, 160))
            canvas.rect(gx, oy + ruler - (14 if major else 5), 1, 14 if major else 5, (0, 0, 0))
            if major and i < w:
                canvas.text(gx + 1, oy + 12, str(x + i), 1, (0, 0, 0), None)
        for i in range(h + 1):
            gy, major = oy + ruler + i * factor, (y + i) % 10 == 0
            if factor >= 6 or major:
                canvas.rect(ox + ruler, gy, tw, 1, (0, 0, 0) if major else (150, 150, 160))
            canvas.rect(ox + ruler - (14 if major else 5), gy, 14 if major else 5, 1, (0, 0, 0))
            if major and i < h:
                canvas.text(ox + 2, gy + 1, str(y + i), 1, (0, 0, 0), None)
        ground, ink, colours = ink_of(crop, w, h)
        inks.append(ink)
        print(f"{path}: background #{ground.hex()}")
        if not ink:
            print("  no ink in the region")
            continue
        x0, y0, x1, y1 = ink
        print(f"  ink from x {x + x0} to {x + x1}, y {y + y0} to {y + y1}: {x1 - x0 + 1} x {y1 - y0 + 1} px = {pt(x1 - x0 + 1, scale)} x {pt(y1 - y0 + 1, scale)} pt")
        top = sorted(colours.items(), key=lambda kv: -kv[1])[:4]
        print("  most common ink colours: " + ", ".join(f"#{c.hex()} {n} px" for c, n in top))
        for line in edge_lines(crop, w, h, region, ink, ground, top[0][0]):
            print(line)
    canvas.save(out)
    print(f"image {out}: the zoom, {canvas.width}x{canvas.height}")
    if len(inks) == 2 and all(inks):
        moves = [f"{side} {inks[1][k] - inks[0][k]:+d} px" for k, side in enumerate(("left", "top", "right", "bottom")) if inks[1][k] != inks[0][k]]
        print("second against first: " + (", ".join(moves) if moves else "the ink box is the same") + f", pt = px / {scale:g}")
