#!/usr/bin/env python
"""Convert OpenEarthMap-SAR checkpoints to cut_lib / pytorch-image-translation-models format.

Saves under models/BiliSakura/OpenEarthMap-SAR with structure compatible with:
- cut_lib CUTPipeline.from_checkpoint() and CUTTranslator.from_checkpoint()
- pytorch-image-translation-models ImageTranslator.from_checkpoint()
"""

from __future__ import annotations

import shutil
from pathlib import Path

import torch

# Source: raw OpenEarthMap-SAR checkpoints (after unzip)
RAW_ROOT = Path("/root/worksapce/models/raw/OpenEarthMap-SAR")
# Target: BiliSakura format for cut_lib inference
OUT_ROOT = Path("/root/worksapce/models/BiliSakura/OpenEarthMap-SAR")

# Model dirs and their epoch numbers (from _net_G.pth filename)
MODELS = [
    ("opt2sar", "20"),
    ("sar2opt", "15"),
    ("seman2opt", "25"),
    ("seman2opt_pesudo", "195"),
    ("seman2sar", "25"),
    ("seman2sar_pesudo", "200"),
]


def main():
    OUT_ROOT.mkdir(parents=True, exist_ok=True)

    for model_name, epoch in MODELS:
        src_dir = RAW_ROOT / model_name
        dst_dir = OUT_ROOT / model_name
        dst_dir.mkdir(parents=True, exist_ok=True)

        src_ckpt = src_dir / f"{epoch}_net_G.pth"
        if not src_ckpt.exists():
            print(f"Skip {model_name}: {src_ckpt} not found")
            continue

        # 1. Copy epoch-specific net_G.pth (cut_lib format)
        dst_epoch = dst_dir / f"{epoch}_net_G.pth"
        shutil.copy2(src_ckpt, dst_epoch)
        print(f"Copied {model_name}: {epoch}_net_G.pth")

        # 2. Copy as latest_net_G.pth for cut_lib epoch="latest"
        dst_latest = dst_dir / "latest_net_G.pth"
        shutil.copy2(src_ckpt, dst_latest)

        # 3. Save pytorch-image-translation-models format: {"generator": state_dict}
        state_dict = torch.load(src_ckpt, map_location="cpu", weights_only=True)
        ckpt_pitm = {"generator": state_dict}
        pitm_path = dst_dir / "generator.pt"
        torch.save(ckpt_pitm, pitm_path)
        print(f"  Saved {model_name}/generator.pt (pytorch-image-translation-models format)")

    print(f"\nDone. Models saved to {OUT_ROOT}")


if __name__ == "__main__":
    main()
