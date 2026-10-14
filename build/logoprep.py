"""Logo helpers: trim transparent padding, erase a subtitle line under a wordmark, measure ink."""
import numpy as np
from PIL import Image


def load_rgba(path):
    return Image.open(path).convert("RGBA")


def trim(im, thresh=12):
    a = np.asarray(im)[:, :, 3]
    ys, xs = np.where(a > thresh)
    if not len(xs):
        return im
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def coverage(im):
    """Share of the trimmed box that is ink; thin or airy marks need more area to read at the same weight."""
    a = np.asarray(im)[:, :, 3]
    return float((a > 128).mean()) if a.size else 1.0


def ink(im):
    """Mean luminance (0-1) and saturation of the opaque pixels."""
    arr = np.asarray(im).astype(float) / 255
    m = arr[:, :, 3] > 0.5
    if not m.any():
        return 1.0, 0.0
    rgb = arr[:, :, :3][m]
    lum = (0.2126 * rgb[:, 0] + 0.7152 * rgb[:, 1] + 0.0722 * rgb[:, 2]).mean()
    sat = (rgb.max(1) - rgb.min(1)).mean()
    return float(lum), float(sat)


def _components(mask):
    """4-connected components of a boolean mask: list of (y0, y1, x0, x1, pixel_indices)."""
    from collections import deque
    h, w = mask.shape
    seen = np.zeros_like(mask)
    out = []
    for sy, sx in zip(*np.nonzero(mask)):
        if seen[sy, sx]:
            continue
        q, pix = deque([(sy, sx)]), []
        seen[sy, sx] = True
        while q:
            y, x = q.popleft()
            pix.append((y, x))
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        ys = [p[0] for p in pix]
        xs = [p[1] for p in pix]
        out.append((min(ys), max(ys) + 1, min(xs), max(xs) + 1, pix))
    return out


def drop_small_lower(im, top_frac=0.5, max_h=0.22, thresh=24, grow=2):
    """Erase small glyph groups that start in the lower part of the logo (a subtitle under the wordmark)."""
    im = trim(im)
    a = np.asarray(im).copy()
    mask = a[:, :, 3] > thresh
    grown = mask.copy()
    for _ in range(grow):  # merge letters of one line sideways only, so stacked lines stay apart
        g = grown.copy()
        g[:, 1:] |= grown[:, :-1]
        g[:, :-1] |= grown[:, 1:]
        grown = g
    h = mask.shape[0]
    for y0, y1, x0, x1, pix in _components(grown):
        if y0 > h * top_frac and (y1 - y0) < h * max_h:
            a[y0:y1, x0:x1, 3] = np.where(grown[y0:y1, x0:x1], 0, a[y0:y1, x0:x1, 3])
    a[:, :, 3] = np.where(a[:, :, 3] < thresh, 0, a[:, :, 3])  # faint glow left behind by erased words
    return trim(Image.fromarray(a))
