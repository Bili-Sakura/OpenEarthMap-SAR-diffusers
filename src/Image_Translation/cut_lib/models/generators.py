"""CUT ResNet generator with intermediate feature extraction.

This module provides a ResNet-based generator compatible with the CUT
(Contrastive Unpaired Translation) training pipeline.  The key extension
over a plain ResNet generator is the ``encode_only`` forward mode that
returns intermediate feature maps at specified layer indices, which is
required for the PatchNCE contrastive loss.
"""

from __future__ import annotations

import functools

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# Anti-aliased down/up-sampling helpers (from the original CUT codebase)
# ---------------------------------------------------------------------------

def _get_filter(filt_size: int = 3) -> torch.Tensor:
    """Return a 2-D low-pass filter kernel of the given size."""
    _kernels = {
        1: np.array([1.0]),
        2: np.array([1.0, 1.0]),
        3: np.array([1.0, 2.0, 1.0]),
        4: np.array([1.0, 3.0, 3.0, 1.0]),
        5: np.array([1.0, 4.0, 6.0, 4.0, 1.0]),
        6: np.array([1.0, 5.0, 10.0, 10.0, 5.0, 1.0]),
        7: np.array([1.0, 6.0, 15.0, 20.0, 15.0, 6.0, 1.0]),
    }
    a = _kernels[filt_size]
    filt = torch.Tensor(a[:, None] * a[None, :])
    return filt / filt.sum()


def _get_pad_layer(pad_type: str):
    if pad_type in ("refl", "reflect"):
        return nn.ReflectionPad2d
    if pad_type in ("repl", "replicate"):
        return nn.ReplicationPad2d
    if pad_type == "zero":
        return nn.ZeroPad2d
    raise ValueError(f"Unsupported padding type: {pad_type}")


class _Downsample(nn.Module):
    """Anti-aliased downsampling layer."""

    def __init__(self, channels: int, pad_type: str = "reflect", filt_size: int = 3, stride: int = 2, pad_off: int = 0):
        super().__init__()
        self.filt_size = filt_size
        self.pad_off = pad_off
        self.pad_sizes = [
            int(1.0 * (filt_size - 1) / 2) + pad_off,
            int(np.ceil(1.0 * (filt_size - 1) / 2)) + pad_off,
            int(1.0 * (filt_size - 1) / 2) + pad_off,
            int(np.ceil(1.0 * (filt_size - 1) / 2)) + pad_off,
        ]
        self.stride = stride
        self.channels = channels

        filt = _get_filter(filt_size=self.filt_size)
        self.register_buffer("filt", filt[None, None, :, :].repeat((self.channels, 1, 1, 1)))

        self.pad = _get_pad_layer(pad_type)(self.pad_sizes)

    def forward(self, inp: torch.Tensor) -> torch.Tensor:
        if self.filt_size == 1:
            if self.pad_off == 0:
                return inp[:, :, :: self.stride, :: self.stride]
            return self.pad(inp)[:, :, :: self.stride, :: self.stride]
        return F.conv2d(self.pad(inp), self.filt, stride=self.stride, groups=inp.shape[1])


class _Upsample(nn.Module):
    """Anti-aliased upsampling layer."""

    def __init__(self, channels: int, pad_type: str = "repl", filt_size: int = 4, stride: int = 2):
        super().__init__()
        self.filt_size = filt_size
        self.filt_odd = np.mod(filt_size, 2) == 1
        self.pad_size = int((filt_size - 1) / 2)
        self.stride = stride
        self.channels = channels

        filt = _get_filter(filt_size=self.filt_size) * (stride ** 2)
        self.register_buffer("filt", filt[None, None, :, :].repeat((self.channels, 1, 1, 1)))

        self.pad = _get_pad_layer(pad_type)([1, 1, 1, 1])

    def forward(self, inp: torch.Tensor) -> torch.Tensor:
        ret = F.conv_transpose2d(
            self.pad(inp), self.filt, stride=self.stride, padding=1 + self.pad_size, groups=inp.shape[1]
        )[:, :, 1:, 1:]
        if self.filt_odd:
            return ret
        return ret[:, :, :-1, :-1]


# ---------------------------------------------------------------------------
# ResNet building blocks
# ---------------------------------------------------------------------------

class _ResnetBlock(nn.Module):
    """Single residual block with two 3×3 convolutions."""

    def __init__(
        self,
        dim: int,
        padding_type: str = "reflect",
        norm_layer: type[nn.Module] = nn.InstanceNorm2d,
        use_dropout: bool = False,
        use_bias: bool = True,
    ) -> None:
        super().__init__()
        layers: list[nn.Module] = []

        p = 0
        if padding_type == "reflect":
            layers.append(nn.ReflectionPad2d(1))
        elif padding_type == "replicate":
            layers.append(nn.ReplicationPad2d(1))
        elif padding_type == "zero":
            p = 1
        else:
            raise NotImplementedError(f"padding [{padding_type}] not implemented")

        layers += [nn.Conv2d(dim, dim, kernel_size=3, padding=p, bias=use_bias), norm_layer(dim), nn.ReLU(True)]
        if use_dropout:
            layers.append(nn.Dropout(0.5))

        p = 0
        if padding_type == "reflect":
            layers.append(nn.ReflectionPad2d(1))
        elif padding_type == "replicate":
            layers.append(nn.ReplicationPad2d(1))
        elif padding_type == "zero":
            p = 1

        layers += [nn.Conv2d(dim, dim, kernel_size=3, padding=p, bias=use_bias), norm_layer(dim)]
        self.conv_block = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.conv_block(x)


# ---------------------------------------------------------------------------
# CUT ResNet Generator
# ---------------------------------------------------------------------------

class CUTResNetGenerator(nn.Module):
    """ResNet-based generator for CUT image-to-image translation.

    This generator supports two forward modes:

    1. **Standard mode** (``layers=[]``): produces an output image.
    2. **Feature extraction mode** (``layers=[0, 4, 8, ...]``): returns
       intermediate feature maps at the requested layer indices.  When
       ``encode_only=True`` only the features are returned (no output
       image), which is the mode used during NCE loss computation.

    The architecture mirrors the original CUT ``ResnetGenerator`` so that
    pre-trained checkpoint weights can be loaded directly.

    Parameters
    ----------
    in_channels:
        Number of input image channels.
    out_channels:
        Number of output image channels.
    base_filters:
        Number of filters in the first convolution layer (``ngf``).
    n_blocks:
        Number of residual blocks.
    norm_layer:
        Normalisation layer constructor.
    use_dropout:
        Whether to use dropout in residual blocks.
    padding_type:
        Padding type for residual blocks.
    no_antialias:
        If ``True`` use strided convolution for downsampling instead
        of anti-aliased downsampling.
    no_antialias_up:
        If ``True`` use transposed convolution for upsampling instead
        of anti-aliased upsampling.
    """

    def __init__(
        self,
        in_channels: int = 3,
        out_channels: int = 3,
        base_filters: int = 64,
        n_blocks: int = 9,
        norm_layer: type[nn.Module] = nn.InstanceNorm2d,
        use_dropout: bool = False,
        padding_type: str = "reflect",
        no_antialias: bool = False,
        no_antialias_up: bool = False,
    ) -> None:
        assert n_blocks >= 0
        super().__init__()

        if isinstance(norm_layer, functools.partial):
            use_bias = norm_layer.func == nn.InstanceNorm2d
        else:
            use_bias = norm_layer == nn.InstanceNorm2d

        model: list[nn.Module] = [
            nn.ReflectionPad2d(3),
            nn.Conv2d(in_channels, base_filters, kernel_size=7, padding=0, bias=use_bias),
            norm_layer(base_filters),
            nn.ReLU(True),
        ]

        # Downsampling
        n_downsampling = 2
        for i in range(n_downsampling):
            mult = 2 ** i
            if no_antialias:
                model += [
                    nn.Conv2d(base_filters * mult, base_filters * mult * 2, kernel_size=3, stride=2, padding=1, bias=use_bias),
                    norm_layer(base_filters * mult * 2),
                    nn.ReLU(True),
                ]
            else:
                model += [
                    nn.Conv2d(base_filters * mult, base_filters * mult * 2, kernel_size=3, stride=1, padding=1, bias=use_bias),
                    norm_layer(base_filters * mult * 2),
                    nn.ReLU(True),
                    _Downsample(base_filters * mult * 2),
                ]

        # Residual blocks
        mult = 2 ** n_downsampling
        for _ in range(n_blocks):
            model.append(
                _ResnetBlock(base_filters * mult, padding_type=padding_type, norm_layer=norm_layer, use_dropout=use_dropout, use_bias=use_bias)
            )

        # Upsampling
        for i in range(n_downsampling):
            mult = 2 ** (n_downsampling - i)
            if no_antialias_up:
                model += [
                    nn.ConvTranspose2d(base_filters * mult, base_filters * mult // 2, kernel_size=3, stride=2, padding=1, output_padding=1, bias=use_bias),
                    norm_layer(base_filters * mult // 2),
                    nn.ReLU(True),
                ]
            else:
                model += [
                    _Upsample(base_filters * mult),
                    nn.Conv2d(base_filters * mult, base_filters * mult // 2, kernel_size=3, stride=1, padding=1, bias=use_bias),
                    norm_layer(base_filters * mult // 2),
                    nn.ReLU(True),
                ]

        model += [nn.ReflectionPad2d(3)]
        model += [nn.Conv2d(base_filters, out_channels, kernel_size=7, padding=0)]
        model += [nn.Tanh()]

        self.model = nn.Sequential(*model)

    def forward(
        self,
        x: torch.Tensor,
        layers: list[int] | None = None,
        encode_only: bool = False,
    ) -> torch.Tensor | tuple[torch.Tensor, list[torch.Tensor]] | list[torch.Tensor]:
        """Forward pass with optional intermediate feature extraction.

        Parameters
        ----------
        x:
            Input tensor ``[B, C, H, W]``.
        layers:
            Layer indices at which to capture intermediate features.
            If ``None`` or empty, runs a standard forward pass.
        encode_only:
            When ``True`` and *layers* is non-empty, return only the
            intermediate features (stop after the last requested layer).

        Returns
        -------
        - Standard mode: output tensor ``[B, C_out, H, W]``.
        - Feature mode (``encode_only=False``): ``(output, features)``.
        - Feature mode (``encode_only=True``): ``features`` list.
        """
        if layers is None:
            layers = []

        if -1 in layers:
            layers = list(layers)
            layers.append(len(self.model))

        if len(layers) > 0:
            feat = x
            feats: list[torch.Tensor] = []
            for layer_id, layer in enumerate(self.model):
                feat = layer(feat)
                if layer_id in layers:
                    feats.append(feat)
                if layer_id == layers[-1] and encode_only:
                    return feats
            return feat, feats

        return self.model(x)
