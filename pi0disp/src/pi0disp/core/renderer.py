"""
Rendering utilities for ST7789V display.

Provides fast RGB→RGB565 color conversion using numpy lookup tables
and region optimization helpers for dirty rectangle rendering.
"""

from typing import List, Tuple

import numpy as np


class ColorConverter:
    """Fast RGB to RGB565 color conversion using cached lookup tables.

    RGB565 encodes each pixel as 16 bits: Red (5 bits) | Green (6 bits) | Blue (5 bits).
    Pre-computed lookup tables eliminate per-pixel bit manipulation.
    """

    def __init__(self):
        """Initialize lookup tables for R, G, B → RGB565 conversion."""
        self._r_lut = (np.arange(256, dtype=np.uint16) >> 3) << 11
        self._g_lut = (np.arange(256, dtype=np.uint16) >> 2) << 5
        self._b_lut = np.arange(256, dtype=np.uint16) >> 3

    def rgb_to_rgb565_bytes(self, rgb_array: np.ndarray) -> bytes:
        """Convert an RGB numpy array to big-endian RGB565 byte string.

        Args:
            rgb_array: NumPy array with shape (height, width, 3), dtype uint8.

        Returns:
            Byte string of RGB565 pixel data (2 bytes per pixel, big-endian).
        """
        r = self._r_lut[rgb_array[:, :, 0]]
        g = self._g_lut[rgb_array[:, :, 1]]
        b = self._b_lut[rgb_array[:, :, 2]]
        rgb565 = r | g | b
        return rgb565.astype(">u2").tobytes()


class RegionOptimizer:
    """Optimizes rectangular regions for partial display updates.

    Provides region clamping (to display boundaries) and merging
    (to reduce the number of SPI transfers for multiple dirty rects).
    """

    @staticmethod
    def clamp_region(
        region: Tuple[int, int, int, int],
        width: int,
        height: int,
    ) -> Tuple[int, int, int, int]:
        """Clamp a region's coordinates to display boundaries.

        Args:
            region: Tuple of (x0, y0, x1, y1).
            width: Display width in pixels.
            height: Display height in pixels.

        Returns:
            Clamped region tuple (x0, y0, x1, y1).
        """
        return (
            max(0, region[0]),
            max(0, region[1]),
            min(width, region[2]),
            min(height, region[3]),
        )

    @staticmethod
    def merge_regions(
        regions: List[Tuple[int, int, int, int]],
        max_regions: int = 8,
        merge_threshold: int = 50,
    ) -> List[Tuple[int, int, int, int]]:
        """Merge overlapping or nearby regions to minimize SPI transfers.

        Args:
            regions: List of (x0, y0, x1, y1) tuples.
            max_regions: Maximum number of regions to return.
            merge_threshold: Max pixel distance to consider regions for merging.

        Returns:
            Optimized list of merged region tuples.
        """
        if len(regions) <= 1:
            return regions

        # Filter out invalid zero/negative-area regions
        valid = [r for r in regions if r and r[2] > r[0] and r[3] > r[1]]
        if not valid:
            return []

        # Sort by area (smallest first) to encourage merging small regions
        sorted_regions = sorted(valid, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
        merged: List[Tuple[int, int, int, int]] = []

        while sorted_regions:
            current = sorted_regions.pop(0)
            was_merged = False
            for i, existing in enumerate(merged):
                if RegionOptimizer._should_merge(current, existing, merge_threshold):
                    merged[i] = RegionOptimizer._merge_two(current, existing)
                    was_merged = True
                    break
            if not was_merged:
                merged.append(current)

        # Aggressive merging if still over limit
        while len(merged) > max_regions:
            min_area_increase = float("inf")
            best_pair = (0, 1)
            for i in range(len(merged)):
                for j in range(i + 1, len(merged)):
                    r1, r2 = merged[i], merged[j]
                    m = RegionOptimizer._merge_two(r1, r2)
                    area_increase = (
                        (m[2] - m[0]) * (m[3] - m[1])
                        - (r1[2] - r1[0]) * (r1[3] - r1[1])
                        - (r2[2] - r2[0]) * (r2[3] - r2[1])
                    )
                    if area_increase < min_area_increase:
                        min_area_increase = area_increase
                        best_pair = (i, j)

            # Pop higher index first, then lower, to avoid shifting
            hi, lo = max(best_pair), min(best_pair)
            merged_region = RegionOptimizer._merge_two(merged[hi], merged[lo])
            merged.pop(hi)
            merged.pop(lo)
            merged.append(merged_region)

        return merged

    @staticmethod
    def _should_merge(
        r1: Tuple[int, int, int, int],
        r2: Tuple[int, int, int, int],
        threshold: int,
    ) -> bool:
        """Check if two regions are close enough to merge."""
        x_overlap = (r1[0] <= r2[2] + threshold) and (r1[2] >= r2[0] - threshold)
        y_overlap = (r1[1] <= r2[3] + threshold) and (r1[3] >= r2[1] - threshold)
        return x_overlap and y_overlap

    @staticmethod
    def _merge_two(
        r1: Tuple[int, int, int, int],
        r2: Tuple[int, int, int, int],
    ) -> Tuple[int, int, int, int]:
        """Merge two regions into their bounding box."""
        return (
            min(r1[0], r2[0]),
            min(r1[1], r2[1]),
            max(r1[2], r2[2]),
            max(r1[3], r2[3]),
        )
