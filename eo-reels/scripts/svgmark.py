"""Rasterize the EO mark SVGs (absolute M/L/H/V/Z paths, even-odd fill) with PIL."""
import re
from PIL import Image, ImageChops, ImageDraw

SS = 4  # supersampling


def _subpaths(d):
    toks = re.findall(r"[MLHVZmlhvz]|-?\d*\.?\d+(?:e-?\d+)?", d)
    polys, cur, x, y, cmd, i = [], [], 0.0, 0.0, None, 0
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd = t.upper()
            i += 1
            if cmd == "Z":
                if cur:
                    polys.append(cur)
                cur = []
            continue
        if cmd == "M":
            if cur:
                polys.append(cur)
            x, y = float(toks[i]), float(toks[i + 1]); i += 2
            cur = [(x, y)]
            cmd = "L"
        elif cmd == "L":
            x, y = float(toks[i]), float(toks[i + 1]); i += 2
            cur.append((x, y))
        elif cmd == "H":
            x = float(toks[i]); i += 1
            cur.append((x, y))
        elif cmd == "V":
            y = float(toks[i]); i += 1
            cur.append((x, y))
        else:
            raise ValueError(f"unsupported path command {cmd}")
    if cur:
        polys.append(cur)
    return polys


def render(svg_path, height, color):
    svg = open(svg_path).read()
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split()]
    scale = height * SS / vb[3]
    W, H = round(vb[2] * scale), round(vb[3] * scale)
    mask = Image.new("L", (W, H), 0)
    for m in re.finditer(r"<path([^>]*)/>", svg):
        attrs = m.group(1)
        d = re.search(r'\bd="([^"]+)"', attrs).group(1)
        tx = ty = 0.0
        tr = re.search(r'translate\(([-\d.]+)[ ,]+([-\d.]+)\)', attrs)
        if tr:
            tx, ty = float(tr.group(1)), float(tr.group(2))
        pm = Image.new("L", (W, H), 0)  # even-odd within one path
        for poly in _subpaths(d):
            sub = Image.new("L", (W, H), 0)
            pts = [((px + tx - vb[0]) * scale, (py + ty - vb[1]) * scale) for px, py in poly]
            ImageDraw.Draw(sub).polygon(pts, fill=255)
            pm = ImageChops.logical_xor(pm.convert("1"), sub.convert("1")).convert("L")
        mask = ImageChops.lighter(mask, pm)
    out = Image.new("RGBA", (W, H), color + (0,))
    out.putalpha(mask)
    return out.resize((round(W / SS), height), Image.LANCZOS)
