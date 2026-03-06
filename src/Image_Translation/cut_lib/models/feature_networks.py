"""Patch sampling and MLP projection networks for CUT.

The ``PatchSampleMLP`` module extracts spatial patches from feature maps
produced by the generator encoder and projects them through a small MLP.
This is the *F* network in the CUT paper that maps features into the
space where contrastive (InfoNCE) loss is computed.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class _L2Normalize(nn.Module):
    """L2-normalise along a given dimension."""

    def __init__(self, dim: int = 1, eps: float = 1e-12) -> None:
        super().__init__()
        self.dim = dim
        self.eps = eps

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return nn.functional.normalize(x, p=2, dim=self.dim, eps=self.eps)


class PatchSampleMLP(nn.Module):
    """Patch sampling + MLP projection head for CUT contrastive loss.

    During the first forward call the per-layer MLPs are lazily created
    based on the channel dimensions of the incoming features (matching
    the original CUT ``PatchSampleF`` behaviour).

    Parameters
    ----------
    use_mlp:
        If ``True``, project each sampled patch through a two-layer MLP.
    projection_dim:
        Output dimension of the MLP heads (``netF_nc`` in the original
        CUT code).
    """

    def __init__(
        self,
        use_mlp: bool = True,
        projection_dim: int = 256,
    ) -> None:
        super().__init__()
        self.use_mlp = use_mlp
        self.projection_dim = projection_dim
        self.l2norm = _L2Normalize(dim=1)
        self._mlp_init = False

    def _create_mlps(self, feats: list[torch.Tensor]) -> None:
        """Lazily create one MLP per feature level."""
        for mlp_id, feat in enumerate(feats):
            input_nc = feat.shape[1]
            mlp = nn.Sequential(
                nn.Linear(input_nc, self.projection_dim),
                nn.ReLU(inplace=True),
                nn.Linear(self.projection_dim, self.projection_dim),
            )
            if feat.is_cuda:
                mlp = mlp.cuda(feat.device)
            self.add_module(f"mlp_{mlp_id}", mlp)
        self._mlp_init = True

    def forward(
        self,
        feats: list[torch.Tensor],
        num_patches: int = 256,
        patch_ids: list[torch.Tensor] | None = None,
    ) -> tuple[list[torch.Tensor], list[torch.Tensor]]:
        """Sample patches from feature maps and optionally project them.

        Parameters
        ----------
        feats:
            List of feature tensors, one per encoder layer, each shaped
            ``[B, C, H, W]``.
        num_patches:
            Number of spatial locations to sample per feature level.
        patch_ids:
            Pre-computed patch indices (for positive-pair consistency).
            If ``None`` indices are randomly sampled.

        Returns
        -------
        (projected_features, patch_ids)
            - ``projected_features``: list of tensors shaped
              ``[B * num_patches, projection_dim]``.
            - ``patch_ids``: list of index tensors (can be reused to
              sample the same locations from a different feature set).
        """
        return_ids: list[torch.Tensor] = []
        return_feats: list[torch.Tensor] = []

        if self.use_mlp and not self._mlp_init:
            self._create_mlps(feats)

        for feat_id, feat in enumerate(feats):
            batch, _channels, height, width = feat.shape
            feat_reshape = feat.permute(0, 2, 3, 1).flatten(1, 2)  # [B, H*W, C]

            if num_patches > 0:
                if patch_ids is not None:
                    patch_id = patch_ids[feat_id]
                else:
                    patch_id = torch.randperm(feat_reshape.shape[1], device=feat.device)
                    patch_id = patch_id[: int(min(num_patches, patch_id.shape[0]))]
                x_sample = feat_reshape[:, patch_id, :].flatten(0, 1)  # [B * P, C]
            else:
                x_sample = feat_reshape
                patch_id = torch.tensor([], device=feat.device)

            if self.use_mlp:
                mlp = getattr(self, f"mlp_{feat_id}")
                x_sample = mlp(x_sample)

            return_ids.append(patch_id)
            x_sample = self.l2norm(x_sample)

            if num_patches == 0:
                x_sample = x_sample.permute(0, 2, 1).reshape(batch, x_sample.shape[-1], height, width)

            return_feats.append(x_sample)

        return return_feats, return_ids
