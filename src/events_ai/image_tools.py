import base64
import io
from pathlib import Path

from PIL import Image


def compress(path: Path, quality: int):
    with Image.open(path) as img:
        img.save(path, "JPEG", optimize=True, quality=50)


def to_b64_url(path: Path) -> str:
    buffer = io.BytesIO()

    with Image.open(path) as img:
        img.save(buffer, format="JPEG")

    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"
