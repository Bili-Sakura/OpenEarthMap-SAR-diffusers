"""CUT (Contrastive Unpaired Translation) library.

A clean, modular reimplementation of the CUT image-to-image translation
method following the ``pytorch-image-translation-models`` library
conventions.  Designed for loading pre-trained CUT checkpoints and
running inference.

Quick start
-----------

**Pipeline API** (tensor in / tensor out)::

    from src.Image_Translation.cut_lib.pipelines import CUTPipeline

    pipeline = CUTPipeline.from_checkpoint("checkpoint/sar2opt_CUT", device="cuda")
    result = pipeline(source_tensor, output_type="pil")

**Translator API** (PIL image in / PIL image out)::

    from src.Image_Translation.cut_lib.inference import CUTTranslator

    translator = CUTTranslator.from_checkpoint("checkpoint/sar2opt_CUT", device="cuda")
    result_img = translator.predict(pil_image)
"""

from src.Image_Translation.cut_lib.inference import CUTTranslator
from src.Image_Translation.cut_lib.losses import PatchNCELoss
from src.Image_Translation.cut_lib.models import CUTResNetGenerator, PatchSampleMLP
from src.Image_Translation.cut_lib.pipelines import CUTPipeline, CUTPipelineOutput

__all__ = [
    # Models
    "CUTResNetGenerator",
    "PatchSampleMLP",
    # Losses
    "PatchNCELoss",
    # Pipelines
    "CUTPipeline",
    "CUTPipelineOutput",
    # Inference
    "CUTTranslator",
]
