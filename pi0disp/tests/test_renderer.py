"""Unit tests for pi0disp.core.renderer module."""

import numpy as np

from pi0disp.core.renderer import ColorConverter, RegionOptimizer


class TestColorConverter:
    """Tests for RGB to RGB565 conversion."""

    def setup_method(self):
        self.converter = ColorConverter()

    def test_pure_red(self):
        """Pure red (255,0,0) should map to 0xF800."""
        img = np.zeros((1, 1, 3), dtype=np.uint8)
        img[0, 0] = [255, 0, 0]
        result = self.converter.rgb_to_rgb565_bytes(img)
        assert len(result) == 2
        value = int.from_bytes(result, "big")
        assert value == 0xF800

    def test_pure_green(self):
        """Pure green (0,255,0) should map to 0x07E0."""
        img = np.zeros((1, 1, 3), dtype=np.uint8)
        img[0, 0] = [0, 255, 0]
        result = self.converter.rgb_to_rgb565_bytes(img)
        value = int.from_bytes(result, "big")
        assert value == 0x07E0

    def test_pure_blue(self):
        """Pure blue (0,0,255) should map to 0x001F."""
        img = np.zeros((1, 1, 3), dtype=np.uint8)
        img[0, 0] = [0, 0, 255]
        result = self.converter.rgb_to_rgb565_bytes(img)
        value = int.from_bytes(result, "big")
        assert value == 0x001F

    def test_pure_white(self):
        """Pure white (255,255,255) should map to 0xFFFF."""
        img = np.zeros((1, 1, 3), dtype=np.uint8)
        img[0, 0] = [255, 255, 255]
        result = self.converter.rgb_to_rgb565_bytes(img)
        value = int.from_bytes(result, "big")
        assert value == 0xFFFF

    def test_pure_black(self):
        """Pure black (0,0,0) should map to 0x0000."""
        img = np.zeros((1, 1, 3), dtype=np.uint8)
        result = self.converter.rgb_to_rgb565_bytes(img)
        value = int.from_bytes(result, "big")
        assert value == 0x0000

    def test_output_size(self):
        """A 240x320 image should produce 240*320*2 = 153600 bytes."""
        img = np.zeros((320, 240, 3), dtype=np.uint8)
        result = self.converter.rgb_to_rgb565_bytes(img)
        assert len(result) == 240 * 320 * 2

    def test_multiple_pixels(self):
        """Test a 2x2 image produces 8 bytes."""
        img = np.zeros((2, 2, 3), dtype=np.uint8)
        img[0, 0] = [255, 0, 0]  # Red
        img[0, 1] = [0, 255, 0]  # Green
        img[1, 0] = [0, 0, 255]  # Blue
        img[1, 1] = [255, 255, 255]  # White
        result = self.converter.rgb_to_rgb565_bytes(img)
        assert len(result) == 8


class TestRegionOptimizer:
    """Tests for region clamping and merging."""

    def test_clamp_within_bounds(self):
        """A region fully within bounds should remain unchanged."""
        region = (10, 20, 100, 200)
        result = RegionOptimizer.clamp_region(region, 240, 320)
        assert result == (10, 20, 100, 200)

    def test_clamp_negative_coords(self):
        """Negative coordinates should be clamped to 0."""
        region = (-10, -20, 100, 200)
        result = RegionOptimizer.clamp_region(region, 240, 320)
        assert result == (0, 0, 100, 200)

    def test_clamp_exceeds_bounds(self):
        """Coordinates exceeding display size should be clamped."""
        region = (10, 20, 300, 400)
        result = RegionOptimizer.clamp_region(region, 240, 320)
        assert result == (10, 20, 240, 320)

    def test_merge_empty(self):
        """Empty list should return empty."""
        result = RegionOptimizer.merge_regions([])
        assert result == []

    def test_merge_single(self):
        """Single region should be returned as-is."""
        regions = [(10, 10, 50, 50)]
        result = RegionOptimizer.merge_regions(regions)
        assert result == [(10, 10, 50, 50)]

    def test_merge_overlapping(self):
        """Two overlapping regions should merge into one bounding box."""
        regions = [(10, 10, 50, 50), (30, 30, 80, 80)]
        result = RegionOptimizer.merge_regions(regions)
        assert len(result) == 1
        assert result[0] == (10, 10, 80, 80)

    def test_merge_distant_regions(self):
        """Two distant regions should remain separate."""
        regions = [(0, 0, 10, 10), (200, 200, 240, 240)]
        result = RegionOptimizer.merge_regions(regions, merge_threshold=10)
        assert len(result) == 2

    def test_merge_invalid_regions(self):
        """Zero and negative area regions should be filtered out."""
        regions = [(10, 10, 10, 10), (20, 20, 15, 15), (30, 30, 50, 50)]
        result = RegionOptimizer.merge_regions(regions)
        assert len(result) == 1
        assert result[0] == (30, 30, 50, 50)

    def test_merge_max_regions(self):
        """Should reduce to max_regions via aggressive merging."""
        regions = [
            (0, 0, 10, 10),
            (20, 20, 30, 30),
            (40, 40, 50, 50),
            (60, 60, 70, 70),
        ]
        result = RegionOptimizer.merge_regions(regions, max_regions=2, merge_threshold=5)
        assert len(result) <= 2
