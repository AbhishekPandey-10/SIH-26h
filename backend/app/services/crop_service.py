"""
Normalized Bounding-Box Image Crop Service with Drift Padding & In-Memory Caching
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs

Crops original document images at normalized coordinates [x, y, w, h] (0.0 to 1.0)
with 8% padding to handle handwriting skew and camera tilt.
Enforces strict coordinate validation and truthful error handling (no blank image synthesis).
"""

import io
import logging
import math
from pathlib import Path
from typing import Dict, Tuple

from PIL import Image

from app.services.session_manager import session_manager

logger = logging.getLogger("medikiosk.crop_service")


class CropService:
    def __init__(self, cache_size: int = 256):
        self._cache: Dict[Tuple[str, float, float, float, float], bytes] = {}
        self.max_cache_size = cache_size

    def clear_cache(self, session_id: str | None = None) -> None:
        """Purges cached crops; if session_id provided, purges paths containing session_id."""
        if not session_id:
            self._cache.clear()
            logger.info("Cleared entire crop cache")
            return
        keys_to_remove = [k for k in self._cache.keys() if session_id in k[0]]
        for k in keys_to_remove:
            self._cache.pop(k, None)
        logger.info(f"Purged {len(keys_to_remove)} crop cache entries for session {session_id}")

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

        Raises:
            ValueError: If coordinates or dimensions are invalid.
            FileNotFoundError: If source image does not exist.
        """
        coords = [x, y, w, h]
        if not all(isinstance(c, (int, float)) and math.isfinite(c) for c in coords):
            raise ValueError(f"Crop coordinates must be finite numbers: {coords}")
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            raise ValueError(f"Crop origin x={x}, y={y} must be between 0.0 and 1.0")
        if w <= 0.0 or h <= 0.0:
            raise ValueError(f"Crop dimensions w={w}, h={h} must be strictly positive")
        if x + w > 1.05 or y + h > 1.05:
            raise ValueError(f"Crop bounding box exceeds image boundaries: x+w={x+w:.4f}, y+h={y+h:.4f}")

        path_obj = Path(image_path).resolve()
        if not path_obj.exists():
            raise FileNotFoundError(f"Source document image not found at {path_obj}")

        path_str = str(path_obj)
        cache_key = (
            path_str,
            round(float(x), 4),
            round(float(y), 4),
            round(float(w), 4),
            round(float(h), 4),
        )

        if cache_key in self._cache:
            return self._cache[cache_key]

        img = Image.open(path_str)
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


async def _crop_cache_cleanup_hook(session_id: str) -> None:
    """Registered encounter lifecycle cleanup hook to purge session crops."""
    crop_service.clear_cache(session_id)


session_manager.register_cleanup_hook(_crop_cache_cleanup_hook)
