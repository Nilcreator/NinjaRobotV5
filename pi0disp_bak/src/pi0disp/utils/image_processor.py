# -*- coding: utf-8 -*-
"""
pi0disp project utility functions.

This module provides high-level utility functions and classes that leverage
the `performance_core` module for optimized operations, such as color
conversion, region management, and image processing.
"""

import numpy as np
from PIL import Image

from .performance_core import create_optimizer_pack

# --- Module-level Singleton ---
_OPTIMIZER_PACK = None

def _get_optimizers():
    """Lazy initializer for the singleton optimizer pack."""
    global _OPTIMIZER_PACK
    if _OPTIMIZER_PACK is None:
        _OPTIMIZER_PACK = create_optimizer_pack()
    return _OPTIMIZER_PACK

# --- High-Level Image Processor ---

class ImageProcessor:
    """
    A utility class for performing common,
    high-level image processing tasks.
    """
    def __init__(self):
        self.optimizers = _get_optimizers()

    def resize_with_aspect_ratio(
            self, 
            img: Image.Image, 
            target_width: int, 
            target_height: int,
            fit_mode: str = "contain"
    ) -> Image.Image:
        """
        Resizes an image while maintaining its aspect ratio.
        """
        img_ratio = img.width / img.height
        target_ratio = target_width / target_height
        
        if fit_mode == "contain":
            if img_ratio > target_ratio:
                new_width = target_width
                new_height = int(target_width / img_ratio)
            else:
                new_height = target_height
                new_width = int(target_height * img_ratio)
        elif fit_mode == "cover":
            if img_ratio < target_ratio:
                new_width = target_width
                new_height = int(target_width / img_ratio)
            else:
                new_height = target_height
                new_width = int(target_height * img_ratio)
        else:
            raise ValueError(f"Unknown fit_mode: {fit_mode}")

        resized = img.resize(
            (new_width, new_height), Image.Resampling.LANCZOS
        )
        
        if fit_mode == "contain":
            # Create a black canvas and paste the resized image in the center
            result = Image.new(
                "RGB", (target_width, target_height), (0, 0, 0)
            )
            paste_x = (target_width - new_width) // 2
            paste_y = (target_height - new_height) // 2
            result.paste(resized, (paste_x, paste_y))
            return result
        
        crop_x = (new_width - target_width) // 2
        crop_y = (new_height - target_height) // 2
        return resized.crop(
            (crop_x, crop_y, crop_x + target_width, crop_y + target_height)
        )
    
    def apply_gamma(
            self, img: Image.Image, gamma: float = 2.2
    ) -> Image.Image:
        """
        Applies gamma correction to an image.
        """
        if img.mode != "RGB":
            img = img.convert("RGB")
        np_img = np.array(img, dtype=np.uint8)
        corrected = self.optimizers['color_converter'].apply_gamma(
            np_img, gamma
        )
        return Image.fromarray(corrected, "RGB")
