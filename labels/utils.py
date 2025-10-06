import io, os
from PIL import Image, ImageDraw, ImageFont
import qrcode
from barcode import Code128, EAN13
from barcode.writer import ImageWriter
import requests
from django.conf import settings

def mm2px(mm, dpi): return round(mm * dpi / 25.4)

def _load_image_from_url(url, target_size=None):
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGBA")
        if target_size:
            img = img.resize(target_size, Image.LANCZOS)
        return img
    except Exception:
        # fallback placeholder
        w, h = target_size or (120, 80)
        ph = Image.new("RGBA", (w, h), (240,240,240,255))
        d = ImageDraw.Draw(ph)
        d.rectangle([(0,0),(w-1,h-1)], outline=(180,180,180,255))
        d.text((6,6), "IMG", fill=(120,120,120,255))
        return ph

def _draw_barcode(value, size_px):
    # try Code128 first (generic)
    try:
        barcode = Code128(value, writer=ImageWriter())
    except Exception:
        # fallback to EAN13 with padded numeric if possible
        try:
            padded = (value if value.isdigit() else "0000000000000")[:13].ljust(13, "0")
            barcode = EAN13(padded, writer=ImageWriter())
        except Exception:
            # return placeholder
            img = Image.new("RGBA", size_px, (255,255,255,255))
            d = ImageDraw.Draw(img)
            d.text((4,4), "BARCODE ERR", fill=(0,0,0,255))
            return img
    out = io.BytesIO()
    barcode.write(out, options={"module_height": size_px[1]//2, "module_width": 0.3})
    out.seek(0)
    img = Image.open(out).convert("RGBA")
    return img.resize(size_px, Image.LANCZOS)

def _draw_qr(value, size_px):
    qr = qrcode.QRCode(box_size=10, border=1)
    qr.add_data(value)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    return img.resize(size_px, Image.LANCZOS)

def render_label_to_image(template, data: dict):
    """Return a PIL Image using template.schema and data keys."""
    W = mm2px(template.width_mm, template.dpi)
    H = mm2px(template.height_mm, template.dpi)
    img = Image.new("RGBA", (W, H), "white")
    draw = ImageDraw.Draw(img)

    # load a basic font; Pillow default if truetype not found
    try:
        font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "DejaVuSans.ttf")
        default_font = ImageFont.truetype(font_path, 12)
    except Exception:
        default_font = ImageFont.load_default()

    elements = (template.schema or {}).get("elements", [])
    for el in elements:
        x, y = int(el.get("x",0)), int(el.get("y",0))
        w, h = int(el.get("w",80)), int(el.get("h",20))
        t = el.get("type")
        key = (el.get("dataKey") or "").strip()
        font_size = int(el.get("fontSize") or 12)
        font = default_font
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            pass

        if t == "text":
            val = data.get(key) or el.get("value") or ""
            draw.text((x, y), str(val), fill=(0,0,0), font=font)

        elif t == "image":
            url = data.get(key)
            thumb = _load_image_from_url(url, (w, h)) if url else _load_image_from_url("", (w, h))
            img.alpha_composite(thumb, (x, y))

        elif t == "barcode":
            val = data.get(key) or data.get("sku") or "CODE"
            bc = _draw_barcode(str(val), (w, h))
            img.alpha_composite(bc, (x, y))

        elif t == "qrcode":
            val = data.get(key) or data.get("sku") or "QR"
            qr = _draw_qr(str(val), (w, h))
            img.alpha_composite(qr, (x, y))

    return img.convert("RGB")
