"""Contrastive (PatchNCE) loss for CUT."""

from __future__ import annotations

import torch
import torch.nn as nn


class PatchNCELoss(nn.Module):
    """Patch-level noise-contrastive estimation loss.

    For each query patch feature, the corresponding key patch at the
    *same* spatial location is the positive, and all other patches in
    the mini-batch act as negatives.

    Parameters
    ----------
    batch_size:
        Training batch size (used to reshape features).
    temperature:
        Softmax temperature (``nce_T`` in the original CUT code).
    """

    def __init__(self, batch_size: int = 1, temperature: float = 0.07) -> None:
        super().__init__()
        self.batch_size = batch_size
        self.temperature = temperature
        self.cross_entropy_loss = nn.CrossEntropyLoss(reduction="none")

    def forward(self, feat_q: torch.Tensor, feat_k: torch.Tensor) -> torch.Tensor:
        """Compute PatchNCE loss.

        Parameters
        ----------
        feat_q:
            Query features from the generated image, shaped
            ``[B * num_patches, dim]``.
        feat_k:
            Key features from the source image, shaped
            ``[B * num_patches, dim]``.

        Returns
        -------
        Per-sample NCE loss tensor.
        """
        num_samples = feat_q.shape[0]
        dim = feat_q.shape[1]
        feat_k = feat_k.detach()

        # Positive logits
        l_pos = torch.bmm(feat_q.view(num_samples, 1, -1), feat_k.view(num_samples, -1, 1))
        l_pos = l_pos.view(num_samples, 1)

        # Negative logits — within current batch
        feat_q = feat_q.view(self.batch_size, -1, dim)
        feat_k = feat_k.view(self.batch_size, -1, dim)
        n_patches = feat_q.size(1)
        l_neg_curbatch = torch.bmm(feat_q, feat_k.transpose(2, 1))

        # Mask out diagonal (same-patch similarity is meaningless)
        diagonal = torch.eye(n_patches, device=feat_q.device, dtype=torch.bool)[None, :, :]
        l_neg_curbatch.masked_fill_(diagonal, -10.0)
        l_neg = l_neg_curbatch.view(-1, n_patches)

        out = torch.cat((l_pos, l_neg), dim=1) / self.temperature

        loss = self.cross_entropy_loss(
            out, torch.zeros(out.size(0), dtype=torch.long, device=feat_q.device)
        )
        return loss
