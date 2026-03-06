"""Loss functions for CUT image translation."""

from src.Image_Translation.cut_lib.losses.contrastive import PatchNCELoss

__all__ = [
    "PatchNCELoss",
]
