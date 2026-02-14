"""
Scan renderer: converts contract text to realistic scanned-document PDFs.

Pipeline per contract:
  1. Render text → crisp high-res PNG via reportlab
  2. Apply scan artifacts (blur, noise, rotation, JPEG compression, paper tint)
  3. Embed degraded image into a single-page PDF via fpdf2

Severity levels control artifact magnitudes:
  LOW    – nearly legible scan (blur 0.5, noise σ=2,  rotation ±0.3°, JPEG 88%)
  MEDIUM – typical office scanner (blur 1.2, noise σ=6,  rotation ±1.0°, JPEG 78%)
  HIGH   – poor-quality scan     (blur 2.0, noise σ=12, rotation ±2.0°, JPEG 68%)
"""

from __future__ import annotations

import io
import math
import random
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PIL import Image, ImageFilter
from fpdf import FPDF
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas

from contract_validator.data.schemas import OcrSeverity


# ---------------------------------------------------------------------------
# Severity parameters
# ---------------------------------------------------------------------------

_SEVERITY_PARAMS: dict[OcrSeverity, dict] = {
    OcrSeverity.LOW: {
        "blur_radius": 0.5,
        "noise_sigma": 2,
        "rotation_range": 0.3,   # degrees, ±
        "skew_range": 0.003,      # tan of angle
        "jpeg_quality": 88,
        "tint_strength": 0.04,    # 0 = no tint, 1 = full yellow
    },
    OcrSeverity.MEDIUM: {
        "blur_radius": 1.2,
        "noise_sigma": 6,
        "rotation_range": 1.0,
        "skew_range": 0.007,
        "jpeg_quality": 78,
        "tint_strength": 0.08,
    },
    OcrSeverity.HIGH: {
        "blur_radius": 2.0,
        "noise_sigma": 12,
        "rotation_range": 2.0,
        "skew_range": 0.012,
        "jpeg_quality": 68,
        "tint_strength": 0.14,
    },
}


# ---------------------------------------------------------------------------
# Step 1: render text → crisp image
# ---------------------------------------------------------------------------

def render_contract_to_image(
    text: str,
    dpi: int = 200,
    font_size: int = 9,
) -> Image.Image:
    """
    Render contract text to a crisp PIL Image using reportlab.

    The image is A4-sized at the requested DPI with a small margin.
    Returns an RGB PIL Image.
    """
    # A4 in points (reportlab default unit)
    page_w_pt, page_h_pt = A4          # 595 × 842 pt
    px_per_pt = dpi / 72.0
    img_w = int(page_w_pt * px_per_pt)
    img_h = int(page_h_pt * px_per_pt)

    # Render to a temporary PDF first, then rasterise via reportlab's renderPDF
    # We use a BytesIO buffer to keep everything in memory.
    pdf_buf = io.BytesIO()
    c = rl_canvas.Canvas(pdf_buf, pagesize=A4)

    margin_pt = 15 * mm
    text_w = page_w_pt - 2 * margin_pt
    usable_h = page_h_pt - 2 * margin_pt

    # Use Courier to match the existing PDF style
    c.setFont("Courier", font_size)
    line_h_pt = font_size * 1.4

    x = margin_pt
    y = page_h_pt - margin_pt  # start from top

    for raw_line in text.splitlines():
        # Word-wrap long lines
        for wrapped in _wrap_line(raw_line, text_w, font_size):
            if y < margin_pt + line_h_pt:
                c.showPage()
                c.setFont("Courier", font_size)
                y = page_h_pt - margin_pt
            c.drawString(x, y - line_h_pt, wrapped)
            y -= line_h_pt

    c.save()
    pdf_buf.seek(0)

    # Rasterise the first page of the PDF using reportlab's renderPM
    try:
        from reportlab.graphics import renderPM
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas as _c  # noqa: F401
        # Use pdfrw or PyMuPDF if available for better rasterisation;
        # fall back to our own PIL-based text renderer if renderPM is unavailable.
        raise ImportError("prefer PIL fallback")  # renderPM needs rlPyCairo
    except ImportError:
        pass

    # PIL fallback: render text directly onto a white PIL Image
    img = _render_text_pil(text, img_w, img_h, dpi, font_size)
    return img


def _wrap_line(line: str, max_width_pt: float, font_size: int) -> list[str]:
    """Very simple character-width word wrapper (Courier is monospace)."""
    char_w_pt = font_size * 0.6  # Courier: width ≈ 0.6 × height
    max_chars = max(1, int(max_width_pt / char_w_pt))
    if len(line) <= max_chars:
        return [line]
    result = []
    while len(line) > max_chars:
        # Try to break at a space
        cut = line.rfind(" ", 0, max_chars)
        if cut == -1:
            cut = max_chars
        result.append(line[:cut])
        line = line[cut:].lstrip()
    if line:
        result.append(line)
    return result


def _render_text_pil(
    text: str,
    img_w: int,
    img_h: int,
    dpi: int,
    font_size: int,
) -> Image.Image:
    """
    Pure-PIL text rendering onto a white A4 canvas.

    Uses PIL's built-in bitmap font (no external font files needed).
    For production quality, reportlab's renderPM with rlPyCairo would be
    preferred, but this keeps the dependency footprint minimal.
    """
    from PIL import ImageDraw, ImageFont

    img = Image.new("RGB", (img_w, img_h), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Try to load a monospace TTF; fall back to PIL default
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont
    font_pt = max(8, int(font_size * dpi / 72))
    try:
        # Common monospace fonts on Linux/Windows/macOS
        for candidate in [
            "cour.ttf",         # Windows Courier New
            "DejaVuSansMono.ttf",
            "LiberationMono-Regular.ttf",
            "Courier New.ttf",
        ]:
            try:
                font = ImageFont.truetype(candidate, font_pt)
                break
            except (OSError, IOError):
                continue
        else:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    margin_px = int(15 * mm * dpi / 72)
    x = margin_px
    y = margin_px

    # Estimate line height from font metrics
    try:
        bbox = font.getbbox("Ag")
        line_h = int((bbox[3] - bbox[1]) * 1.5)
    except AttributeError:
        line_h = font_pt + 4

    for raw_line in text.splitlines():
        for wrapped in _wrap_line(raw_line, img_w - 2 * margin_px, font_pt):
            if y + line_h > img_h - margin_px:
                break  # single-page only; multi-page handled by caller
            draw.text((x, y), wrapped, fill=(10, 10, 10), font=font)
            y += line_h

    return img


# ---------------------------------------------------------------------------
# Step 2: apply scan artifacts
# ---------------------------------------------------------------------------

def apply_scan_artifacts(
    img: Image.Image,
    severity: OcrSeverity,
    rng: Optional[random.Random] = None,
) -> Image.Image:
    """
    Apply a realistic scan-artifact pipeline to a crisp PIL Image.

    Stages (in order):
      1. Paper tint (slight yellow/warm bias)
      2. Gaussian blur (lens focus imperfection)
      3. Additive Gaussian noise (sensor noise)
      4. Small rotation (paper misalignment on scanner glass)
      5. Horizontal skew (perspective distortion)
      6. JPEG re-encode (scanner compression)

    Returns a new RGB PIL Image.
    """
    if rng is None:
        rng = random.Random()

    p = _SEVERITY_PARAMS[severity]
    arr = np.array(img, dtype=np.float32)

    # 1. Paper tint — warm yellowed paper
    strength = p["tint_strength"]
    arr[:, :, 0] = np.clip(arr[:, :, 0] + 255 * strength * 0.6, 0, 255)   # R+
    arr[:, :, 1] = np.clip(arr[:, :, 1] + 255 * strength * 0.4, 0, 255)   # G+
    arr[:, :, 2] = np.clip(arr[:, :, 2] - 255 * strength * 0.2, 0, 255)   # B-

    # 2. Gaussian blur
    result = Image.fromarray(arr.astype(np.uint8))
    if p["blur_radius"] > 0:
        result = result.filter(ImageFilter.GaussianBlur(radius=p["blur_radius"]))
    arr = np.array(result, dtype=np.float32)

    # 3. Additive Gaussian noise
    sigma = p["noise_sigma"]
    if sigma > 0:
        noise = rng.gauss(0, sigma)  # scalar seed; vectorise below
        noise_arr = np.random.default_rng(
            abs(int(noise * 1000)) % (2**31)
        ).normal(0, sigma, arr.shape).astype(np.float32)
        arr = np.clip(arr + noise_arr, 0, 255)

    result = Image.fromarray(arr.astype(np.uint8))

    # 4. Small rotation (expand=True keeps full content; crop back to original size)
    angle = rng.uniform(-p["rotation_range"], p["rotation_range"])
    if abs(angle) > 0.05:
        result = result.rotate(
            angle,
            resample=Image.BILINEAR,
            expand=False,
            fillcolor=(245, 242, 235),  # paper-coloured fill
        )

    # 5. Horizontal skew (affine transform)
    skew = rng.uniform(-p["skew_range"], p["skew_range"])
    if abs(skew) > 0.0005:
        result = _apply_skew(result, skew)

    # 6. JPEG re-encode (lossy compression artifact)
    jpeg_buf = io.BytesIO()
    result.convert("RGB").save(jpeg_buf, format="JPEG", quality=p["jpeg_quality"])
    jpeg_buf.seek(0)
    result = Image.open(jpeg_buf).copy()

    return result


def _apply_skew(img: Image.Image, skew: float) -> Image.Image:
    """Apply a horizontal shear (skew) transform to a PIL image."""
    w, h = img.size
    # Affine coefficients for PIL: (a, b, c, d, e, f) where
    # x_src = a*x_dst + b*y_dst + c
    # y_src = d*x_dst + e*y_dst + f
    # Horizontal shear: x_src = x_dst + skew * y_dst
    a, b, c = 1, skew, -skew * h / 2   # centre the skew
    d, e, f = 0, 1, 0
    result = img.transform(
        (w, h),
        Image.AFFINE,
        (a, b, c, d, e, f),
        resample=Image.BILINEAR,
        fillcolor=(245, 242, 235),
    )
    return result


# ---------------------------------------------------------------------------
# Step 3: embed image into PDF
# ---------------------------------------------------------------------------

def image_to_pdf(img: Image.Image, output_path: Path) -> None:
    """
    Embed a PIL Image as the sole page of an A4 PDF using fpdf2.

    The image is scaled to fill the page (preserving aspect ratio).
    """
    # Save image to a temporary file; fpdf2 needs a file path or bytes
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        img.convert("RGB").save(str(tmp_path), format="JPEG", quality=92)

        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_margins(0, 0, 0)
        pdf.set_auto_page_break(False)
        pdf.add_page()

        # A4 dimensions in mm
        page_w_mm, page_h_mm = 210, 297

        img_w, img_h = img.size
        img_aspect = img_w / img_h
        page_aspect = page_w_mm / page_h_mm

        if img_aspect >= page_aspect:
            # wider than page — fit to width
            draw_w, draw_h = page_w_mm, page_w_mm / img_aspect
        else:
            # taller than page — fit to height
            draw_w, draw_h = page_h_mm * img_aspect, page_h_mm

        # Centre on page
        x = (page_w_mm - draw_w) / 2
        y = (page_h_mm - draw_h) / 2

        pdf.image(str(tmp_path), x=x, y=y, w=draw_w, h=draw_h)
        pdf.output(str(output_path))
    finally:
        tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Convenience entry point
# ---------------------------------------------------------------------------

def render_scanned_pdf(
    contract_text: str,
    output_path: Path,
    severity: OcrSeverity,
    dpi: int = 200,
    seed: Optional[int] = None,
) -> None:
    """
    Full pipeline: text → crisp image → scan artifacts → PDF.

    Args:
        contract_text: The raw contract string.
        output_path:   Where to write the resulting PDF.
        severity:      Scan artifact severity level.
        dpi:           Render resolution (default 200 dpi, good balance of speed/quality).
        seed:          Optional RNG seed for reproducibility.
    """
    rng = random.Random(seed)
    img = render_contract_to_image(contract_text, dpi=dpi)
    img = apply_scan_artifacts(img, severity, rng=rng)
    image_to_pdf(img, output_path)
