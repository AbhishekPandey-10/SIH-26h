"""
Normalized Bounding-Box Image Crop Service with Drift Padding & In-Memory Caching
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Crops original document images at normalized coordinates [x, y, w, h] (0.0 to 1.0)
with 8% padding to handle handwriting skew and camera tilt.
"""

import io
import logging
from pathlib import Path
from typing import Dict, Tuple

from PIL import Image

logger = logging.getLogger("medikiosk.crop_service")


class CropService:
    def __init__(self, cache_size: int = 256):
        self._cache: Dict[Tuple[str, float, float, float, float], bytes] = {}
        self.max_cache_size = cache_size

    def crop_document(
        self,
        image_path: Path | str,
        x: float,
        y: float,
        w: float,
        h: float,
        padding: float = 0.08,
    ) -> bytes:
        """
        Crop an image using normalized coordinates [x, y, w, h] with padding.

        Args:
            image_path: Path to the source image.
            x: Normalized left coordinate (0.0 to 1.0).
            y: Normalized top coordinate (0.0 to 1.0).
            w: Normalized width (0.0 to 1.0).
            h: Normalized height (0.0 to 1.0).
            padding: Additional fractional padding (default 8% = 0.08).

        Returns:
            JPEG image bytes of the cropped region.
        """
        path_str = str(Path(image_path).resolve())
        cache_key = (
            path_str,
            round(float(x), 4),
            round(float(y), 4),
            round(float(w), 4),
            round(float(h), 4),
        )

        if cache_key in self._cache:
            return self._cache[cache_key]

        if not Path(path_str).exists():
            raise FileNotFoundError(f"Source image not found: {path_str}")

        with Image.open(path_str) as img:
            img_w, img_h = img.size

            # Apply 8% padding to prevent OCR boundary clipping
            pad_x = w * padding
            pad_y = h * padding

            norm_x1 = max(0.0, x - pad_x)
            norm_y1 = max(0.0, y - pad_y)
            norm_x2 = min(1.0, x + w + pad_x)
            norm_y2 = min(1.0, y + h + pad_y)

            px_x1 = int(norm_x1 * img_w)
            px_y1 = int(norm_y1 * img_h)
            px_x2 = int(norm_x2 * img_w)
            px_y2 = int(norm_y2 * img_h)

            # Safeguard minimum bounds
            if px_x2 <= px_x1:
                px_x2 = min(img_w, px_x1 + 10)
            if px_y2 <= px_y1:
                px_y2 = min(img_h, px_y1 + 10)

            cropped = img.crop((px_x1, px_y1, px_x2, px_y2))

            # Convert to RGB if needed (e.g. RGBA PNG or palette images)
            if cropped.mode in ("RGBA", "P", "LA"):
                cropped = cropped.convert("RGB")

            buf = io.BytesIO()
            cropped.save(buf, format="JPEG", quality=90)
            jpeg_bytes = buf.getvalue()

            # Maintain LRU cache size
            if len(self._cache) >= self.max_cache_size:
                self._cache.pop(next(iter(self._cache)))

            self._cache[cache_key] = jpeg_bytes
            return jpeg_bytes


crop_service = CropService()
