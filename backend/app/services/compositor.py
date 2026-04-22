# Created by Metrum AI for AMD

"""Pillow-based ad compositor. Overlays headline, body, CTA, and logo
onto a generated image. Text is always rendered programmatically --
never passed to diffusion models."""

import io
import logging
from pathlib import Path

import httpx
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

log = logging.getLogger(__name__)

_FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"
_FALLBACK_FONT = _FONT_DIR / "Inter-Variable.ttf"

MARGIN_RATIO = 0.055
CTA_SIZE_RATIO = 0.022
GRADIENT_START_RATIO = 0.42
GRADIENT_MAX_ALPHA = 230
TEXT_ZONE_TOP_RATIO = 0.62
LINE_SPACING = 1.35
BOTTOM_PAD_RATIO = 0.04
BLUR_REGION_RATIO = 0.40
BLUR_RADIUS = 28
LOGO_MAX_RATIO = 0.14

HEADLINE_MAX_RATIO = 0.050
HEADLINE_MIN_RATIO = 0.028
BODY_MAX_RATIO = 0.025
BODY_MIN_RATIO = 0.016


def _hex_to_rgb(
    value: str, default: tuple[int, int, int]
) -> tuple[int, int, int]:
    if value.startswith("#") and len(value) >= 7:
        try:
            return (
                int(value[1:3], 16),
                int(value[3:5], 16),
                int(value[5:7], 16),
            )
        except ValueError:
            return default
    return default


def _luma(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    if name:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            log.warning("Font %r not found, falling back to Inter", name)
    try:
        return ImageFont.truetype(str(_FALLBACK_FONT), size)
    except OSError:
        log.warning("Fallback font not found, using Pillow default")
        return ImageFont.load_default()


def _wrap_text_px(
    text: str, font: ImageFont.FreeTypeFont, max_width: int
) -> list[str]:
    """Word-wrap text using actual pixel measurements."""
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        test = current + " " + word
        if font.getlength(test) <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _measure_block(lines: list[str], font_size: int) -> int:
    """Total pixel height of a block of text lines."""
    if not lines:
        return 0
    return int(len(lines) * font_size * LINE_SPACING)


def _load_image(url: str, max_size: int = 120) -> Image.Image | None:
    """Load an image from a data-URI, HTTP(S) URL, or s3:// path."""
    try:
        if url.startswith("data:"):
            import base64

            _, encoded = url.split(",", 1)
            raw = base64.b64decode(encoded)
            img = Image.open(io.BytesIO(raw)).convert("RGBA")
        elif url.startswith("s3://"):
            from app.services.minio_client import download_bytes

            raw = download_bytes(url)
            img = Image.open(io.BytesIO(raw)).convert("RGBA")
        else:
            resp = httpx.get(url, timeout=10, follow_redirects=True)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        img.thumbnail((max_size, max_size), Image.LANCZOS)
        return img
    except Exception as exc:
        log.warning("Failed to load image from %s: %s", url[:80], exc)
        return None


def _tight_alpha_cutout(
    img: Image.Image, alpha_cutoff: int = 80
) -> Image.Image:
    """Crop to the real visible subject and discard faint alpha padding.

    Some PNG cutouts contain a wide band of low-alpha edge pixels around the
    subject. Those pixels still count toward the bounding box and create a boxy
    halo. Treat low alpha as fully transparent, crop tightly, then keep the
    cleaned alpha mask on the returned image.
    """
    src = img.convert("RGBA")
    alpha = src.split()[-1]
    cleaned_alpha = alpha.point(lambda a: 255 if a >= alpha_cutoff else 0)
    bbox = cleaned_alpha.getbbox()
    if not bbox:
        return src

    src = src.crop(bbox)
    alpha = alpha.crop(bbox)
    cleaned_alpha = cleaned_alpha.crop(bbox)

    # Keep a slightly softened version of the cleaned mask so the edge does not
    # look stair-stepped, but never reintroduce the wide faint transparent band.
    softened_alpha = cleaned_alpha.filter(ImageFilter.GaussianBlur(radius=0.8))
    src.putalpha(ImageChops.multiply(alpha, softened_alpha))
    return src


def _soften_subject_edges(img: Image.Image) -> Image.Image:
    """Feather and slightly contract subject edges to remove dark matte fringing."""
    src = img.convert("RGBA")
    alpha = src.split()[-1]

    # Pull the mask inward a little so any black edge contamination
    # from the original background gets trimmed away.
    contracted = alpha.filter(ImageFilter.MinFilter(size=3))
    softened = contracted.filter(ImageFilter.GaussianBlur(radius=1.4))

    src.putalpha(softened)

    bbox = softened.getbbox()
    if bbox:
        src = src.crop(bbox)
    return src


def _apply_bottom_blur(img: Image.Image) -> Image.Image:
    """Blur the bottom of the image with a soft feathered transition
    so the boundary between sharp and blurred is invisible."""
    w, h = img.size
    blur_top = int(h * (1.0 - BLUR_REGION_RATIO))
    feather_h = int(h * 0.10)

    fully_blurred = img.filter(ImageFilter.GaussianBlur(radius=BLUR_RADIUS))

    # Build a gradient mask: 0 (sharp) at top of feather zone,
    # 255 (fully blurred) at blur_top + feather_h and below.
    mask = Image.new("L", (w, h), 0)
    feather_start = blur_top - feather_h
    for y in range(feather_start, h):
        if y < blur_top:
            alpha = int(255 * (y - feather_start) / max(1, feather_h))
        else:
            alpha = 255
        mask.paste(alpha, (0, y, w, y + 1))

    img = Image.composite(fully_blurred, img, mask)
    return img


def _fit_text_sizes(
    headline: str,
    body: str,
    cta_h: int,
    max_width: int,
    avail_h: int,
    h_img: int,
    font_name_headline: str,
    font_name_body: str,
) -> tuple[int, list[str], int, list[str]]:
    """Iteratively shrink headline/body font sizes until everything fits
    within avail_h pixels. Returns (headline_size, headline_lines,
    body_size, body_lines)."""
    def gap_headline_body(hs):
        return int(hs * 0.4)

    def gap_body_cta(bs):
        return int(bs * 0.6)

    h_size = max(24, int(h_img * HEADLINE_MAX_RATIO))
    h_min = max(20, int(h_img * HEADLINE_MIN_RATIO))
    b_size = max(14, int(h_img * BODY_MAX_RATIO))
    b_min = max(12, int(h_img * BODY_MIN_RATIO))

    while h_size >= h_min:
        h_font = _load_font(font_name_headline, h_size)
        h_lines = _wrap_text_px(headline, h_font, max_width)
        h_block = _measure_block(h_lines, h_size)

        b_s = min(b_size, int(h_size * 0.55))
        b_s = max(b_s, b_min)
        b_font = _load_font(font_name_body, b_s)
        b_lines = _wrap_text_px(body, b_font, max_width)
        b_block = _measure_block(b_lines, b_s)

        total = (
            h_block
            + gap_headline_body(h_size)
            + b_block
            + gap_body_cta(b_s)
            + cta_h
        )
        if total <= avail_h:
            return h_size, h_lines, b_s, b_lines

        h_size -= 2

    h_font = _load_font(font_name_headline, h_min)
    h_lines = _wrap_text_px(headline, h_font, max_width)
    b_font = _load_font(font_name_body, b_min)
    b_lines = _wrap_text_px(body, b_font, max_width)
    # If body still overflows, truncate it
    h_block = _measure_block(h_lines, h_min)
    remaining = (
        avail_h
        - h_block
        - gap_headline_body(h_min)
        - gap_body_cta(b_min)
        - cta_h
    )
    if remaining > 0:
        max_body = max(0, int(remaining / (b_min * LINE_SPACING)))
        b_lines = b_lines[:max_body]
    else:
        b_lines = []
    return h_min, h_lines, b_min, b_lines


def _fit_video_headline_single_line(
    headline: str,
    max_width: int,
    h_img: int,
    font_name_headline: str,
) -> tuple[int, list[str]]:
    """Prefer a single-line video headline by shrinking the font to fit."""
    h_size = max(18, int(h_img * VIDEO_HEADLINE_MAX_RATIO))
    h_min = max(14, int(h_img * VIDEO_HEADLINE_MIN_RATIO))

    while h_size >= h_min:
        h_font = _load_font(font_name_headline, h_size)
        if h_font.getlength(headline or "") <= max_width:
            return h_size, [headline or ""]
        h_size -= 1

    h_font = _load_font(font_name_headline, h_min)
    h_lines = _wrap_text_px(headline or "", h_font, max_width)
    if len(h_lines) > 2:
        h_lines = h_lines[:2]
    return h_min, h_lines


def compose_ad(
    image_bytes: bytes,
    headline: str,
    body: str,
    cta: str,
    brand_colors: dict,
    brand_fonts: dict,
    logo_url: str | None = None,
    target_size: tuple[int, int] = (1080, 1350),
) -> bytes:
    """Composite headline, body, and CTA onto a hero image."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    img = img.resize(target_size, Image.LANCZOS)
    img = _apply_bottom_blur(img)

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    w, h = img.size
    margin = int(w * MARGIN_RATIO)
    max_text_width = w - margin * 2
    bottom_pad = int(h * BOTTOM_PAD_RATIO)
    max_bottom = h - bottom_pad

    # Gradient
    gradient_top = int(h * GRADIENT_START_RATIO)
    for y in range(gradient_top, h):
        progress = (y - gradient_top) / (h - gradient_top)
        alpha = int(GRADIENT_MAX_ALPHA * (progress**0.7))
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

    # CTA metrics (fixed size)
    cta_size = max(18, int(h * CTA_SIZE_RATIO))
    cta_font = _load_font(brand_fonts.get("cta", ""), cta_size)
    cta_bbox = draw.textbbox((0, 0), cta, font=cta_font)
    cta_text_w = cta_bbox[2] - cta_bbox[0]
    cta_text_h = cta_bbox[3] - cta_bbox[1]
    pad_x, pad_y = int(cta_size * 1.2), int(cta_size * 0.5)
    cta_total_h = cta_text_h + pad_y * 2

    # Available vertical space for all text
    text_top = int(h * TEXT_ZONE_TOP_RATIO)
    avail_h = max_bottom - text_top

    # Dynamically fit headline + body
    accent_rgb = _hex_to_rgb(
        brand_colors.get("accent", "#e91e63"), (233, 30, 99)
    )
    primary_rgb = _hex_to_rgb(
        brand_colors.get("primary", "#ED1C24"), (237, 28, 36)
    )
    cta_fill_rgb = primary_rgb if _luma(accent_rgb) > 185 else accent_rgb

    h_size, h_lines, b_size, b_lines = _fit_text_sizes(
        headline,
        body,
        cta_total_h,
        max_text_width,
        avail_h,
        h,
        brand_fonts.get("headline", ""),
        brand_fonts.get("body", ""),
    )

    headline_font = _load_font(brand_fonts.get("headline", ""), h_size)
    body_font = _load_font(brand_fonts.get("body", ""), b_size)
    h_line_h = int(h_size * LINE_SPACING)
    b_line_h = int(b_size * LINE_SPACING)

    # Draw headline
    cursor_y = text_top
    for line in h_lines:
        draw.text(
            (margin, cursor_y),
            line,
            font=headline_font,
            fill=(255, 255, 255, 255),
        )
        cursor_y += h_line_h

    # Draw body
    cursor_y += int(h_size * 0.4)
    for line in b_lines:
        draw.text(
            (margin, cursor_y), line, font=body_font, fill=(220, 220, 220, 240)
        )
        cursor_y += b_line_h

    # Draw CTA
    cursor_y += int(b_size * 0.6)
    if cursor_y + cta_total_h > max_bottom:
        cursor_y = max_bottom - cta_total_h

    cta_rect = [
        margin,
        cursor_y,
        margin + cta_text_w + pad_x * 2,
        cursor_y + cta_total_h,
    ]
    draw.rounded_rectangle(
        cta_rect, radius=int(cta_size * 0.4), fill=(*cta_fill_rgb, 240)
    )
    draw.rounded_rectangle(
        cta_rect,
        radius=int(cta_size * 0.4),
        outline=(255, 255, 255, 80),
        width=max(1, int(cta_size * 0.08)),
    )
    draw.text(
        (margin + pad_x, cursor_y + pad_y),
        cta,
        font=cta_font,
        fill=(255, 255, 255, 255),
    )

    result = Image.alpha_composite(img, overlay)

    if logo_url:
        logo = _load_image(logo_url, max_size=int(w * LOGO_MAX_RATIO))
        if logo:
            result.paste(logo, (margin, margin), logo)

    result = result.convert("RGB")
    buf = io.BytesIO()
    result.save(buf, format="PNG", quality=95)
    return buf.getvalue()


VIDEO_GRADIENT_START_RATIO = 0.68
VIDEO_TEXT_ZONE_TOP_RATIO = 0.74
VIDEO_GRADIENT_MAX_ALPHA = 200
VIDEO_BOTTOM_PAD_RATIO = 0.03
VIDEO_HEADLINE_MAX_RATIO = 0.035
VIDEO_HEADLINE_MIN_RATIO = 0.022
VIDEO_BODY_MAX_RATIO = 0.018
VIDEO_BODY_MIN_RATIO = 0.013


def compose_overlay_layer(
    headline: str,
    body: str,
    cta: str,
    brand_colors: dict,
    brand_fonts: dict,
    logo_url: str | None = None,
    target_size: tuple[int, int] = (1024, 1024),
) -> bytes:
    """Create transparent copy/logo overlay PNG for video compositing.

    Text is confined to the bottom ~25% of the frame so it doesn't
    obscure the generated video content."""
    overlay = Image.new("RGBA", target_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    w, h = target_size
    margin = int(w * MARGIN_RATIO)
    max_text_width = int(w * 0.55)
    bottom_pad = int(h * VIDEO_BOTTOM_PAD_RATIO)
    max_bottom = h - bottom_pad

    gradient_top = int(h * VIDEO_GRADIENT_START_RATIO)
    for y in range(gradient_top, h):
        progress = (y - gradient_top) / max(1, (h - gradient_top))
        alpha = int(VIDEO_GRADIENT_MAX_ALPHA * (progress**0.6))
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

    cta_size = max(12, int(h * CTA_SIZE_RATIO))
    cta_font = _load_font(brand_fonts.get("cta", ""), cta_size)
    cta_text = cta or ""
    cta_total_h = 0
    cta_text_w = 0
    pad_x, pad_y = int(cta_size * 1.0), int(cta_size * 0.45)
    if cta_text:
        cta_bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
        cta_text_w = cta_bbox[2] - cta_bbox[0]
        cta_text_h = cta_bbox[3] - cta_bbox[1]
        cta_total_h = cta_text_h + pad_y * 2

    text_top = int(h * VIDEO_TEXT_ZONE_TOP_RATIO)

    accent_rgb = _hex_to_rgb(
        brand_colors.get("accent", "#e91e63"), (233, 30, 99)
    )
    primary_rgb = _hex_to_rgb(
        brand_colors.get("primary", "#ED1C24"), (237, 28, 36)
    )
    cta_fill_rgb = primary_rgb if _luma(accent_rgb) > 185 else accent_rgb

    b_size = max(12, int(h * VIDEO_BODY_MAX_RATIO))

    h_size, h_lines = _fit_video_headline_single_line(
        headline or "",
        max_text_width,
        h,
        brand_fonts.get("headline", ""),
    )
    h_font = _load_font(brand_fonts.get("headline", ""), h_size)

    b_font = _load_font(brand_fonts.get("body", ""), b_size)
    b_lines = _wrap_text_px(body or "", b_font, max_text_width)
    if len(b_lines) > 2:
        b_lines = b_lines[:2]

    h_line_h = int(h_size * LINE_SPACING)
    b_line_h = int(b_size * LINE_SPACING)

    cursor_y = text_top
    for line in h_lines:
        draw.text(
            (margin, cursor_y), line, font=h_font, fill=(255, 255, 255, 255)
        )
        cursor_y += h_line_h

    cursor_y += int(h_size * 0.25)
    for line in b_lines:
        draw.text(
            (margin, cursor_y), line, font=b_font, fill=(220, 220, 220, 230)
        )
        cursor_y += b_line_h

    cursor_y += int(b_size * 0.4)
    if cta_text:
        if cursor_y + cta_total_h > max_bottom:
            cursor_y = max_bottom - cta_total_h
        cta_rect = [
            margin,
            cursor_y,
            margin + cta_text_w + pad_x * 2,
            cursor_y + cta_total_h,
        ]
        draw.rounded_rectangle(
            cta_rect, radius=int(cta_size * 0.4), fill=(*cta_fill_rgb, 240)
        )
        draw.rounded_rectangle(
            cta_rect,
            radius=int(cta_size * 0.4),
            outline=(255, 255, 255, 80),
            width=max(1, int(cta_size * 0.08)),
        )
        draw.text(
            (margin + pad_x, cursor_y + pad_y),
            cta_text,
            font=cta_font,
            fill=(255, 255, 255, 255),
        )

    logo_inset = int(w * 0.018)
    if logo_url:
        logo = _load_image(logo_url, max_size=int(w * LOGO_MAX_RATIO))
        if logo:
            overlay.paste(logo, (logo_inset, logo_inset), logo)

    buf = io.BytesIO()
    overlay.save(buf, format="PNG")
    return buf.getvalue()


def compose_reference_layer(
    reference_image_url: str,
    target_size: tuple[int, int] = (1024, 1024),
) -> bytes | None:
    """Return a transparent PNG with the reference / product image centred.

    The image is rendered at ~65% of frame size at full opacity.
    Returns None when the image cannot be loaded."""
    w, h = target_size
    ref_max = int(min(w, h) * 0.65)
    ref_img = _load_image(reference_image_url, max_size=ref_max)
    if ref_img is None:
        return None

    # Tighten the cutout to the real visible subject before adding glow.
    ref_img = _tight_alpha_cutout(ref_img)
    ref_img = _soften_subject_edges(ref_img)

    canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
    rx = (w - ref_img.width) // 2
    ry = (h - ref_img.height) // 2

    # Build the glow on a padded canvas so the blur is not clipped to the
    # product image rectangle, which can create hard boxy corners.
    alpha = ref_img.split()[-1]
    halo_blur = max(28, int(ref_img.width * 0.055))
    halo_pad = halo_blur * 2
    halo_w = ref_img.width + halo_pad * 2
    halo_h = ref_img.height + halo_pad * 2

    halo_mask = Image.new("L", (halo_w, halo_h), 0)
    halo_mask.paste(alpha, (halo_pad, halo_pad))
    halo_mask = halo_mask.filter(ImageFilter.MaxFilter(size=17))
    halo_mask = halo_mask.filter(ImageFilter.GaussianBlur(radius=halo_blur))

    halo_layer = Image.new("RGBA", (halo_w, halo_h), (255, 255, 255, 150))
    halo_layer.putalpha(halo_mask)
    canvas.paste(halo_layer, (rx - halo_pad, ry - halo_pad), halo_layer)

    canvas.paste(ref_img, (rx, ry), ref_img)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()
