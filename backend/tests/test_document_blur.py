"""Unit tests for sensitive-document privacy blur."""
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

from app.services.document_blur import (
    SENSITIVE_DOC_TYPES,
    create_blurred_preview,
    has_blurred_preview,
    is_image_filename,
    is_sensitive_doc_type,
)


def _sample_jpeg() -> bytes:
    img = Image.new("RGB", (320, 200), (20, 40, 80))
    draw = ImageDraw.Draw(img)
    draw.text((24, 80), "SECRET-ID-999", fill=(255, 255, 0))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_sensitive_doc_types_cover_pii_heavy_uploads():
    assert is_sensitive_doc_type("passport")
    assert is_sensitive_doc_type("financial")
    assert not is_sensitive_doc_type("sop")
    assert "passport" in SENSITIVE_DOC_TYPES


def test_image_filename_detection():
    assert is_image_filename("scan.PNG")
    assert is_image_filename("id.webp")
    assert not is_image_filename("statement.pdf")


def test_create_blurred_preview_writes_sibling(tmp_path: Path):
    original = tmp_path / "passport_abcd1234_scan.jpg"
    content = _sample_jpeg()
    original.write_bytes(content)

    preview = create_blurred_preview(content, str(original))
    assert preview is not None
    assert Path(preview).exists()
    assert preview.endswith(".blurred.jpg")
    assert has_blurred_preview(str(original))

    blurred = Image.open(preview)
    assert blurred.size[0] <= 1280
    assert blurred.size[1] <= 1280
