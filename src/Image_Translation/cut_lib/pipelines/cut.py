"""CUT inference pipeline.

Provides a high-level ``CUTPipeline`` that wraps a
:class:`CUTResNetGenerator` for single-pass image translation and
supports loading pre-trained CUT checkpoints produced by the original
training scripts.
"""

from __future__ import annotations

import functools
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn

from src.Image_Translation.cut_lib.models.generators import CUTResNetGenerator

logger = logging.getLogger(__name__)


@dataclass
class CUTPipelineOutput:
    """Container for CUT pipeline results.

    Attributes
    ----------
    images:
        Translated images in the requested format (tensor / PIL / numpy).
    """

    images: Any


class CUTPipeline:
    """End-to-end inference pipeline for a pre-trained CUT generator.

    Parameters
    ----------
    generator:
        A :class:`CUTResNetGenerator` (or any ``nn.Module`` with a
        compatible ``forward`` signature).
    device:
        Device for inference.

    Example
    -------
    >>> from src.Image_Translation.cut_lib.pipelines.cut import CUTPipeline
    >>> pipeline = CUTPipeline.from_checkpoint(
    ...     checkpoint_dir="checkpoint/sar2opt_CUT",
    ...     epoch="latest",
    ...     device="cpu",
    ... )
    >>> result = pipeline(source_tensor, output_type="pil")
    """

    def __init__(
        self,
        generator: nn.Module,
        device: str | torch.device = "cpu",
    ) -> None:
        self.device = torch.device(device)
        self.generator = generator.to(self.device).eval()

    # ------------------------------------------------------------------
    # Factory – load from original CUT checkpoint
    # ------------------------------------------------------------------

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint_dir: str | Path,
        epoch: str = "latest",
        in_channels: int = 3,
        out_channels: int = 3,
        base_filters: int = 64,
        n_blocks: int = 9,
        norm: str = "instance",
        no_antialias: bool = False,
        no_antialias_up: bool = False,
        device: str = "cpu",
    ) -> "CUTPipeline":
        """Load a CUT pipeline from an original CUT checkpoint directory.

        The original CUT training saves generator weights as
        ``{epoch}_net_G.pth`` inside the experiment checkpoint directory.

        Parameters
        ----------
        checkpoint_dir:
            Path to the checkpoint directory (e.g.
            ``checkpoint/sar2opt_CUT``).
        epoch:
            Epoch label (``"latest"``, ``"best"``, or a number as string).
        in_channels, out_channels, base_filters, n_blocks:
            Generator architecture parameters – must match the ones
            used during training.
        norm:
            Normalisation type (``"instance"`` or ``"batch"``).
        no_antialias, no_antialias_up:
            Whether anti-aliased sampling was disabled during training.
        device:
            Target device.
        """
        checkpoint_dir = Path(checkpoint_dir)
        ckpt_path = checkpoint_dir / f"{epoch}_net_G.pth"

        norm_layer: type[nn.Module]
        if norm == "instance":
            norm_layer = functools.partial(nn.InstanceNorm2d, affine=False, track_running_stats=False)
        elif norm == "batch":
            norm_layer = functools.partial(nn.BatchNorm2d, affine=True, track_running_stats=True)
        else:
            raise ValueError(f"Unsupported norm type: {norm}")

        generator = CUTResNetGenerator(
            in_channels=in_channels,
            out_channels=out_channels,
            base_filters=base_filters,
            n_blocks=n_blocks,
            norm_layer=norm_layer,
            use_dropout=False,
            no_antialias=no_antialias,
            no_antialias_up=no_antialias_up,
        )

        state_dict = torch.load(ckpt_path, map_location=device, weights_only=True)
        generator.load_state_dict(state_dict)
        logger.info("Loaded CUT generator from %s", ckpt_path)

        return cls(generator, device=device)

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    @torch.no_grad()
    def __call__(
        self,
        source: torch.Tensor,
        output_type: str = "pt",
    ) -> CUTPipelineOutput:
        """Translate source images.

        Parameters
        ----------
        source:
            Source image tensor ``[B, C, H, W]`` in ``[-1, 1]`` range.
        output_type:
            ``"pt"`` (tensor), ``"pil"`` (list of PIL images), or
            ``"np"`` (numpy array).

        Returns
        -------
        CUTPipelineOutput
        """
        source = source.to(self.device)
        output = self.generator(source)

        return self._format_output(output, output_type)

    # ------------------------------------------------------------------
    # Output formatting (same convention as pytorch-image-translation-models)
    # ------------------------------------------------------------------

    @staticmethod
    def _format_output(tensor: torch.Tensor, output_type: str) -> CUTPipelineOutput:
        if output_type == "pt":
            return CUTPipelineOutput(images=tensor)

        if output_type == "np":
            return CUTPipelineOutput(images=tensor.cpu().numpy())

        if output_type == "pil":
            from PIL import Image

            images: list[Image.Image] = []
            arr = tensor.clamp(-1, 1).cpu()
            arr = (arr + 1.0) / 2.0  # [-1, 1] -> [0, 1]
            for i in range(arr.shape[0]):
                img_np = arr[i].permute(1, 2, 0).numpy()
                img_np = (img_np * 255).astype(np.uint8)
                if img_np.shape[2] == 1:
                    img_np = img_np[:, :, 0]
                images.append(Image.fromarray(img_np))
            return CUTPipelineOutput(images=images)

        raise ValueError(f"Unknown output_type: {output_type!r}")
