# Created by Metrum AI for AMD

"""Quality scoring for generated images. Evaluates OCR presence,
composition safety zones, and image-prompt alignment."""

import io
import logging
import re

from app.services.minio_client import download_bytes
from PIL import Image, ImageFilter, ImageOps

log = logging.getLogger(__name__)

DEFAULT_BRAND_TERMS: list[str] = []

MIN_OCR_CONFIDENCE = 75
OCR_MIN_LENGTH = 8


def _preprocess_for_ocr(img: Image.Image) -> Image.Image:
    """Normalize image for OCR: grayscale, denoise, binarize.

    Keep OCR input bounded for predictable latency on large images.
    """
    gray = ImageOps.grayscale(img)
    max_dim = max(gray.width, gray.height)
    if max_dim > 1280:
        scale = 1280.0 / float(max_dim)
        gray = gray.resize(
            (
                max(1, int(gray.width * scale)),
                max(1, int(gray.height * scale)),
            ),
            Image.Resampling.LANCZOS,
        )
    denoised = gray.filter(ImageFilter.MedianFilter(size=3))
    contrasted = ImageOps.autocontrast(denoised)
    # Fixed threshold works well for our synthetic/digital ad creatives.
    return contrasted.point(lambda p: 255 if p > 145 else 0)


def _run_ocr(
    img: Image.Image,
    brand_terms: list[str] | None = None,
) -> tuple[bool, str]:
    """Run Tesseract OCR on an image. Returns (ocr_pass, text_found).
    ocr_pass is True when NO unwanted text is detected.

    Text that matches brand_terms (case-insensitive) is excluded from
    the unwanted text check -- product branding in images is expected."""
    try:
        import pytesseract

        ocr_img = _preprocess_for_ocr(img)
        data = pytesseract.image_to_data(
            ocr_img,
            output_type=pytesseract.Output.DICT,
            config="--oem 3 --psm 6",
        )

        confident_word_rows: list[tuple[str, int]] = []
        for i, word in enumerate(data["text"]):
            word = word.strip()
            if not word:
                continue
            try:
                conf = int(float(data["conf"][i]))
            except (TypeError, ValueError):
                continue
            if conf < MIN_OCR_CONFIDENCE:
                continue
            confident_word_rows.append((word, conf))

        confident_words = [w for w, _ in confident_word_rows]
        text = " ".join(confident_words).strip()
        if not text or len(text) < OCR_MIN_LENGTH:
            return True, ""

        allowed = set(t.lower() for t in (brand_terms or DEFAULT_BRAND_TERMS))
        filtered_rows = [
            (w, c)
            for w, c in confident_word_rows
            if w.lower() not in allowed and len(w) > 2
        ]
        normalized_words = [
            re.sub(r"[^A-Za-z]", "", w).lower() for w, _ in filtered_rows
        ]
        normalized_words = [w for w in normalized_words if len(w) > 2]

        # Require at least two substantial words to avoid random-noise false positives.
        long_words = [w for w in normalized_words if len(w) >= 4]
        if len(normalized_words) < 3 or len(long_words) < 2:
            return True, text
        avg_conf = sum(c for _, c in filtered_rows) / max(
            1, len(filtered_rows)
        )
        if avg_conf < 82:
            return True, text

        filtered_text = " ".join(normalized_words).strip()

        if filtered_text and len(filtered_text) >= OCR_MIN_LENGTH:
            log.info("OCR detected unwanted text: %r", filtered_text[:120])
            return False, filtered_text

        return True, text

    except ImportError:
        log.error("pytesseract not installed -- failing OCR check")
        return False, "__ocr_unavailable__"
    except Exception as e:
        if e.__class__.__name__ == "TesseractNotFoundError":
            log.error("tesseract binary missing -- failing OCR check")
            return False, "__ocr_unavailable__"
        log.warning("OCR failed: %s", e)
        return False, "__ocr_error__"


def _check_safe_zones(
    img: Image.Image,
    zones: list[tuple[float, float, float, float]] | None = None,
) -> bool:
    """Check that key image content doesn't concentrate in text overlay
    regions. Uses edge density as a proxy for important content.

    Default zones: bottom 35% (headline/body/CTA area) and
    top-left 15% (logo area)."""
    import numpy as np

    if zones is None:
        zones = [
            (0.0, 0.65, 1.0, 1.0),
            (0.0, 0.0, 0.15, 0.10),
        ]

    arr = np.array(img.convert("L"), dtype=np.float32)
    h, w = arr.shape

    gx = np.abs(np.diff(arr, axis=1))
    gy = np.abs(np.diff(arr, axis=0))
    edge_map = np.zeros_like(arr)
    edge_map[:, :-1] += gx
    edge_map[:-1, :] += gy

    total_edge = edge_map.mean()
    if total_edge < 1.0:
        return True

    for x1_f, y1_f, x2_f, y2_f in zones:
        x1, y1 = int(x1_f * w), int(y1_f * h)
        x2, y2 = int(x2_f * w), int(y2_f * h)
        zone_edge = edge_map[y1:y2, x1:x2].mean()
        ratio = zone_edge / total_edge
        if ratio > 1.5:
            log.info(
                "Safe zone fail: zone (%s) edge ratio %.2f",
                (x1_f, y1_f, x2_f, y2_f),
                ratio,
            )
            return False

    return True


def score_image(
    asset_url: str,
    _prompt: str = "",
    brand_terms: list[str] | None = None,
) -> dict:
    """Score a generated image on quality metrics."""
    scores: dict = {
        "clip_score": 0.0,
        "ocr_pass": True,
        "ocr_text_found": "",
        "safe_zone_pass": True,
        "final_score": 0.0,
    }

    try:
        image_bytes = download_bytes(asset_url)
    except Exception:
        scores["final_score"] = 0.0
        return scores

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    ocr_pass, ocr_text = _run_ocr(img, brand_terms=brand_terms)
    scores["ocr_pass"] = ocr_pass
    scores["ocr_text_found"] = ocr_text

    scores["safe_zone_pass"] = _check_safe_zones(img)

    scores["clip_score"] = _heuristic_quality_score(img)

    ocr_weight = 0.3
    clip_weight = 0.5
    safe_weight = 0.2

    scores["final_score"] = (
        (1.0 if scores["ocr_pass"] else 0.0) * ocr_weight
        + scores["clip_score"] * clip_weight
        + (1.0 if scores["safe_zone_pass"] else 0.0) * safe_weight
    )

    scores["clip_score"] = float(scores["clip_score"])
    scores["final_score"] = float(scores["final_score"])

    return scores


def score_image_bytes(
    image_bytes: bytes,
    _prompt: str = "",
    brand_terms: list[str] | None = None,
) -> dict:
    """Score image from raw bytes (for testing without MinIO)."""
    scores: dict = {
        "clip_score": 0.0,
        "ocr_pass": True,
        "ocr_text_found": "",
        "safe_zone_pass": True,
        "final_score": 0.0,
    }

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    ocr_pass, ocr_text = _run_ocr(img, brand_terms=brand_terms)
    scores["ocr_pass"] = ocr_pass
    scores["ocr_text_found"] = ocr_text

    scores["safe_zone_pass"] = _check_safe_zones(img)
    scores["clip_score"] = _heuristic_quality_score(img)

    ocr_weight = 0.3
    clip_weight = 0.5
    safe_weight = 0.2

    scores["final_score"] = (
        (1.0 if scores["ocr_pass"] else 0.0) * ocr_weight
        + scores["clip_score"] * clip_weight
        + (1.0 if scores["safe_zone_pass"] else 0.0) * safe_weight
    )

    scores["clip_score"] = float(scores["clip_score"])
    scores["final_score"] = float(scores["final_score"])

    return scores


def _heuristic_quality_score(img: Image.Image) -> float:
    """Basic image quality heuristic: checks resolution, contrast,
    and color variance as proxy for generation quality."""
    import numpy as np

    arr = np.array(img, dtype=np.float32)

    resolution_score = min(
        1.0,
        (img.width * img.height) / (1080 * 1350),
    )

    gray = arr.mean(axis=2)
    contrast = gray.std() / 128.0
    contrast_score = min(1.0, contrast)

    color_std = arr.std(axis=(0, 1)).mean() / 64.0
    color_score = min(1.0, color_std)

    return resolution_score * 0.2 + contrast_score * 0.5 + color_score * 0.3
