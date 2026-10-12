"""Privacy blur for sensitive student document previews (passport, financial, etc.)."""
from __future__ import annotations

import os
from io import BytesIO

from PIL import Image, ImageFilter

# Doc types that default to a blurred preview (PII / financial exposure).
SENSITIVE_DOC_TYPES = frozenset({"passport", "financial", "transcript", "ielts", "lor"})

IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"})

# Strong enough that passport numbers / account digits are unreadable at a glance.
DEFAULT_BLUR_RADIUS = 28


def is_image_filename(filename: str | None) -> bool:
    if not filename:
        return False
    _, ext = os.path.splitext(filename.lower())
    return ext in IMAGE_EXTENSIONS


def is_sensitive_doc_type(doc_type: str) -> bool:
    return doc_type in SENSITIVE_DOC_TYPES


def blurred_preview_path(original_path: str) -> str:
    """Convention: sibling file with `.blurred.jpg` suffix."""
    return f"{original_path}.blurred.jpg"


def create_blurred_preview(
    content: bytes,
    original_path: str,
    *,
    radius: int = DEFAULT_BLUR_RADIUS,
) -> str | None:
    """
    Write a heavily Gaussian-blurred JPEG preview next to the original file.
    Returns the preview path, or None if the bytes are not a usable image.
    """
    try:
        with Image.open(BytesIO(content)) as img:
            rgb = img.convert("RGB")
            rgb.thumbnail((1280, 1280))
            blurred = rgb.filter(ImageFilter.GaussianBlur(radius=radius))
            out_path = blurred_preview_path(original_path)
            blurred.save(out_path, format="JPEG", quality=72, optimize=True)
            return out_path
    except Exception:
        return None


def has_blurred_preview(file_path: str | None) -> bool:
    if not file_path:
        return False
    return os.path.isfile(blurred_preview_path(file_path))
