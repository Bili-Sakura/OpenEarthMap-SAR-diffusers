"""CUT model architectures."""

from src.Image_Translation.cut_lib.models.feature_networks import PatchSampleMLP
from src.Image_Translation.cut_lib.models.generators import CUTResNetGenerator

__all__ = [
    "CUTResNetGenerator",
    "PatchSampleMLP",
]
