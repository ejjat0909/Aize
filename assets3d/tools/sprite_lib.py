"""Compositing + resampling helpers shared by pack_atlas / verify_sprites / simulate_runtime (Pillow only).

Blender writes STRAIGHT alpha with black RGB under transparent pixels.  Resizing that directly pulls black into every
semi-transparent edge pixel (the classic dark fringe), so all resampling here happens in PREMULTIPLIED space.
"""
import json
import os

import numpy as np
from PIL import Image, ImageChops, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
TOKENS = os.path.join(REPO, "design", "tokens", "aize-purple.tokens.json")

# shadow look (tunable here without re-rendering): tint = purple.950, opacity, blur as a fraction of the frame width
SHADOW = {"tint_token": "color.purple.950", "opacity": 0.46, "blur_frac": 0.012}


def pname(p):
    """File-name token for a pitch: 'p30' for 30, 'p07d50' for 7.5 (identical to blender/render_sprites.pname)."""
    p = float(p)
    return f"p{int(p):02d}" if p.is_integer() else f"p{int(p):02d}d{int(round((p - int(p)) * 100)):02d}"


def pkey(p):
    """Canonical dictionary key / manifest string for a pitch: '30', '7.5'."""
    return f"{float(p):g}"


def token_hex(path):
    t = json.load(open(TOKENS))
    for part in path.split("."):
        t = t[part]
    return t


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ------------------------------------------------------------------------------------------------ premultiplied ops
def premultiply(im):
    """Straight-alpha RGBA -> premultiplied RGBA (8-bit; used by the metrics, not by the resampler)."""
    r, g, b, a = im.split()
    return Image.merge("RGBA", (ImageChops.multiply(r, a), ImageChops.multiply(g, a), ImageChops.multiply(b, a), a))


def to_float(im):
    return np.asarray(im.convert("RGBA"), dtype=np.float32) / 255.0


def from_float(arr):
    return Image.fromarray(np.clip(np.rint(arr * 255.0), 0, 255).astype(np.uint8), "RGBA")


def _resize_plane(plane, size, resample):
    return np.asarray(Image.fromarray(plane.astype(np.float32), "F").resize((size, size), resample), dtype=np.float32)


def resize_rgba(im, size, resample=Image.LANCZOS):
    """Fringe-free resize of a straight-alpha RGBA image, in float precision.

    Colour is weighted by alpha before filtering (premultiplied), the filter runs on 32-bit float planes (no 8-bit
    quantisation of low-alpha edge pixels), and colour is divided by the filtered alpha afterwards.  Lanczos ringing is
    clamped.  Resizing RGB and A as independent planes - the usual accident - leaves a dark halo, see verify_sprites --selftest.
    """
    if im.size == (size, size):
        return im
    arr = to_float(im)
    a = arr[..., 3]
    planes = [_resize_plane(arr[..., i] * a, size, resample) for i in range(3)]
    a2 = np.clip(_resize_plane(a, size, resample), 0.0, 1.0)
    out = np.zeros((size, size, 4), dtype=np.float32)
    ok = a2 > 1e-4
    for i in range(3):
        out[..., i] = np.where(ok, np.clip(planes[i] / np.maximum(a2, 1e-4), 0.0, 1.0), 0.0)
    out[..., 3] = a2
    return from_float(out)


def resize_rgba_naive(im, size, resample=Image.LANCZOS):
    """What NOT to do: filter colour and alpha independently (black under transparent pixels bleeds into the edge)."""
    chans = [c.resize((size, size), resample) for c in im.convert("RGBA").split()]
    return Image.merge("RGBA", chans)


# ------------------------------------------------------------------------------------------------ layer compositing
def shadow_layer(sh_path, size, tint_hex=None, opacity=None, blur_frac=None):
    """Half-res black-alpha shadow render -> full-size tinted, softened RGBA layer."""
    tint = hex_rgb(tint_hex or token_hex(SHADOW["tint_token"]))
    op = SHADOW["opacity"] if opacity is None else opacity
    bl = SHADOW["blur_frac"] if blur_frac is None else blur_frac
    sh = Image.open(sh_path).convert("RGBA")
    a = sh.split()[3].resize((size, size), Image.BICUBIC)
    if bl > 0:
        a = a.filter(ImageFilter.GaussianBlur(bl * size))
    a = a.point(lambda v: int(round(v * op)))
    layer = Image.new("RGBA", (size, size), tint + (0,))
    layer.putalpha(a)
    return layer


def compose_frame(obj_path, sh_path=None, **shadow_kw):
    """Object layer over its tinted shadow -> final straight-alpha RGBA sprite at the render size."""
    obj = Image.open(obj_path).convert("RGBA")
    if sh_path and os.path.exists(sh_path):
        base = shadow_layer(sh_path, obj.size[0], **shadow_kw)
        base.alpha_composite(obj)
        return base
    return obj


def over(bg_rgb, im):
    """Composite an RGBA sprite over a flat colour -> RGB (for previews)."""
    bg = Image.new("RGBA", im.size, tuple(bg_rgb) + (255,))
    bg.alpha_composite(im)
    return bg.convert("RGB")


def alpha_bbox(im, thresh=8):
    a = im.split()[3].point(lambda v: 255 if v >= thresh else 0)
    return a.getbbox()
