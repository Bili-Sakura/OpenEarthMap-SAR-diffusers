"""High-level inference wrapper for CUT generators.

Provides :class:`CUTTranslator`, a convenience class that mirrors the
:class:`~src.inference.predictor.ImageTranslator` API from
``pytorch-image-translation-models`` but is tailored for CUT generators
(including checkpoint loading from the original CUT training format).
"""

from __future__ import annotations

import functools
import logging
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms

from src.Image_Translation.cut_lib.models.generators import CUTResNetGenerator

logger = logging.getLogger(__name__)


class CUTTranslator:
    """High-level inference wrapper for a trained CUT generator.

    Parameters
    ----------
    generator:
        A trained :class:`CUTResNetGenerator`.
    device:
        Device to run inference on.
    image_size:
        Target spatial size for the input transform.
    normalize:
        Whether inputs are normalised to ``[-1, 1]``.
    """

    def __init__(
        self,
        generator: nn.Module,
        device: str | torch.device = "cpu",
        image_size: int = 256,
        normalize: bool = True,
    ) -> None:
        self.device = torch.device(device)
        self.generator = generator.to(self.device).eval()
        self.normalize = normalize

        transform_list: list = [
            transforms.Resize(
                (image_size, image_size),
                transforms.InterpolationMode.BICUBIC,
            ),
            transforms.ToTensor(),
        ]
        if normalize:
            transform_list.append(transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)))
        self.transform = transforms.Compose(transform_list)

    # ------------------------------------------------------------------
    # Factory
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
        image_size: int = 256,
        **kwargs,
    ) -> "CUTTranslator":
        """Create a translator from an original CUT checkpoint.

        Parameters
        ----------
        checkpoint_dir:
            Directory containing ``{epoch}_net_G.pth``.
        epoch:
            Epoch label.
        device:
            Target device.
        image_size:
            Image resize target.
        **kwargs:
            Extra keyword arguments forwarded to the constructor.
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

        return cls(generator, device=device, image_size=image_size, **kwargs)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @torch.no_grad()
    def predict(self, image: Image.Image) -> Image.Image:
        """Translate a single PIL image.

        Parameters
        ----------
        image:
            Input RGB image.

        Returns
        -------
        PIL.Image.Image
            Translated RGB image.
        """
        tensor = self.transform(image.convert("RGB")).unsqueeze(0).to(self.device)
        output = self.generator(tensor).squeeze(0).cpu()
        return self._tensor_to_pil(output)

    @torch.no_grad()
    def predict_batch(self, images: list[Image.Image]) -> list[Image.Image]:
        """Translate a batch of PIL images.

        Parameters
        ----------
        images:
            List of input RGB images.

        Returns
        -------
        list[PIL.Image.Image]
        """
        tensors = torch.stack([self.transform(img.convert("RGB")) for img in images]).to(self.device)
        outputs = self.generator(tensors).cpu()
        return [self._tensor_to_pil(t) for t in outputs]

    def predict_file(self, input_path: str | Path, output_path: str | Path) -> None:
        """Translate an image file and save the result.

        Parameters
        ----------
        input_path:
            Path to the input image.
        output_path:
            Where to save the translated image.
        """
        image = Image.open(input_path).convert("RGB")
        result = self.predict(image)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        result.save(output_path)
        logger.info("Saved translated image to %s", output_path)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _tensor_to_pil(self, tensor: torch.Tensor) -> Image.Image:
        if self.normalize:
            tensor = tensor * 0.5 + 0.5  # [-1, 1] -> [0, 1]
        tensor = tensor.clamp(0, 1)
        return transforms.ToPILImage()(tensor)
