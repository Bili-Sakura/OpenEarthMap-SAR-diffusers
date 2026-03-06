"""Tests for the CUT library — generators, feature networks, losses, pipeline, and inference."""

import functools

import torch
import torch.nn as nn
from PIL import Image

from src.Image_Translation.cut_lib.models.generators import CUTResNetGenerator
from src.Image_Translation.cut_lib.models.feature_networks import PatchSampleMLP
from src.Image_Translation.cut_lib.losses.contrastive import PatchNCELoss
from src.Image_Translation.cut_lib.pipelines.cut import CUTPipeline, CUTPipelineOutput
from src.Image_Translation.cut_lib.inference.predictor import CUTTranslator


# ====================================================================
# Generator tests
# ====================================================================


class TestCUTResNetGenerator:
    """Tests for CUTResNetGenerator."""

    def test_standard_forward_shape(self):
        gen = CUTResNetGenerator(
            in_channels=3, out_channels=3, base_filters=16,
            n_blocks=2, no_antialias=True, no_antialias_up=True,
        )
        x = torch.randn(1, 3, 64, 64)
        y = gen(x)
        assert y.shape == (1, 3, 64, 64)

    def test_output_range(self):
        gen = CUTResNetGenerator(
            in_channels=3, out_channels=3, base_filters=16,
            n_blocks=2, no_antialias=True, no_antialias_up=True,
        )
        x = torch.randn(1, 3, 64, 64)
        y = gen(x)
        assert y.min() >= -1.0
        assert y.max() <= 1.0

    def test_different_channels(self):
        gen = CUTResNetGenerator(
            in_channels=1, out_channels=4, base_filters=16,
            n_blocks=2, no_antialias=True, no_antialias_up=True,
        )
        x = torch.randn(1, 1, 64, 64)
        y = gen(x)
        assert y.shape == (1, 4, 64, 64)

    def test_feature_extraction_encode_only(self):
        gen = CUTResNetGenerator(
            in_channels=3, out_channels=3, base_filters=16,
            n_blocks=2, no_antialias=True, no_antialias_up=True,
        )
        x = torch.randn(1, 3, 64, 64)
        layers = [0, 2, 4]
        feats = gen(x, layers=layers, encode_only=True)
        assert isinstance(feats, list)
        assert len(feats) == 3
        for f in feats:
            assert isinstance(f, torch.Tensor)
            assert f.shape[0] == 1

    def test_feature_extraction_with_output(self):
        gen = CUTResNetGenerator(
            in_channels=3, out_channels=3, base_filters=16,
            n_blocks=2, no_antialias=True, no_antialias_up=True,
        )
        x = torch.randn(1, 3, 64, 64)
        layers = [0, 2]
        result = gen(x, layers=layers, encode_only=False)
        assert isinstance(result, tuple)
        output, feats = result
        assert output.shape == (1, 3, 64, 64)
        assert len(feats) == 2

    def test_antialias_forward(self):
        gen = CUTResNetGenerator(
            in_channels=3, out_channels=3, base_filters=16,
            n_blocks=2, no_antialias=False, no_antialias_up=False,
        )
        x = torch.randn(1, 3, 64, 64)
        y = gen(x)
        assert y.shape == (1, 3, 64, 64)

    def test_batch_forward(self):
        gen = CUTResNetGenerator(
            in_channels=3, out_channels=3, base_filters=16,
            n_blocks=2, no_antialias=True, no_antialias_up=True,
        )
        x = torch.randn(2, 3, 64, 64)
        y = gen(x)
        assert y.shape == (2, 3, 64, 64)

    def test_instance_norm_partial(self):
        norm_layer = functools.partial(nn.InstanceNorm2d, affine=False, track_running_stats=False)
        gen = CUTResNetGenerator(
            in_channels=3, out_channels=3, base_filters=16,
            n_blocks=2, norm_layer=norm_layer,
            no_antialias=True, no_antialias_up=True,
        )
        x = torch.randn(1, 3, 64, 64)
        y = gen(x)
        assert y.shape == (1, 3, 64, 64)


# ====================================================================
# Feature network tests
# ====================================================================


class TestPatchSampleMLP:
    """Tests for PatchSampleMLP."""

    def test_forward_creates_mlps(self):
        net = PatchSampleMLP(use_mlp=True, projection_dim=64)
        feats = [torch.randn(1, 32, 8, 8), torch.randn(1, 64, 4, 4)]
        projected, ids = net(feats, num_patches=16)
        assert len(projected) == 2
        assert len(ids) == 2
        for p in projected:
            assert p.shape[-1] == 64

    def test_forward_without_mlp(self):
        net = PatchSampleMLP(use_mlp=False)
        feats = [torch.randn(1, 32, 8, 8)]
        projected, ids = net(feats, num_patches=16)
        assert len(projected) == 1
        assert projected[0].shape[-1] == 32

    def test_reuse_patch_ids(self):
        net = PatchSampleMLP(use_mlp=True, projection_dim=64)
        feats1 = [torch.randn(1, 32, 8, 8)]
        feats2 = [torch.randn(1, 32, 8, 8)]
        proj1, ids1 = net(feats1, num_patches=16)
        proj2, ids2 = net(feats2, num_patches=16, patch_ids=ids1)
        assert torch.equal(ids1[0], ids2[0])

    def test_l2_normalization(self):
        net = PatchSampleMLP(use_mlp=True, projection_dim=64)
        feats = [torch.randn(1, 32, 8, 8)]
        projected, _ = net(feats, num_patches=16)
        norms = projected[0].norm(dim=1)
        assert torch.allclose(norms, torch.ones_like(norms), atol=1e-5)


# ====================================================================
# Loss tests
# ====================================================================


class TestPatchNCELoss:
    """Tests for PatchNCELoss."""

    def test_output_shape(self):
        loss_fn = PatchNCELoss(batch_size=1, temperature=0.07)
        feat_q = torch.randn(16, 64)
        feat_k = torch.randn(16, 64)
        loss = loss_fn(feat_q, feat_k)
        assert loss.shape == (16,)

    def test_loss_nonnegative(self):
        loss_fn = PatchNCELoss(batch_size=1, temperature=0.07)
        feat_q = torch.randn(16, 64)
        feat_k = torch.randn(16, 64)
        loss = loss_fn(feat_q, feat_k)
        assert (loss >= 0).all()

    def test_identical_features_low_loss(self):
        loss_fn = PatchNCELoss(batch_size=1, temperature=0.07)
        feat = torch.randn(16, 64)
        feat = nn.functional.normalize(feat, dim=1)
        loss_same = loss_fn(feat, feat.clone()).mean()
        loss_diff = loss_fn(feat, torch.randn_like(feat)).mean()
        assert loss_same < loss_diff

    def test_batch_size_2(self):
        loss_fn = PatchNCELoss(batch_size=2, temperature=0.07)
        feat_q = torch.randn(32, 64)
        feat_k = torch.randn(32, 64)
        loss = loss_fn(feat_q, feat_k)
        assert loss.shape == (32,)


# ====================================================================
# Pipeline tests
# ====================================================================


class TestCUTPipeline:
    """Tests for CUTPipeline."""

    def _make_pipeline(self):
        gen = CUTResNetGenerator(
            in_channels=3, out_channels=3, base_filters=16,
            n_blocks=2, no_antialias=True, no_antialias_up=True,
        )
        return CUTPipeline(gen, device="cpu")

    def test_pt_output(self):
        pipeline = self._make_pipeline()
        source = torch.randn(1, 3, 64, 64)
        result = pipeline(source, output_type="pt")
        assert isinstance(result, CUTPipelineOutput)
        assert isinstance(result.images, torch.Tensor)
        assert result.images.shape == (1, 3, 64, 64)

    def test_np_output(self):
        import numpy as np

        pipeline = self._make_pipeline()
        source = torch.randn(1, 3, 64, 64)
        result = pipeline(source, output_type="np")
        assert isinstance(result.images, np.ndarray)

    def test_pil_output(self):
        pipeline = self._make_pipeline()
        source = torch.randn(1, 3, 64, 64)
        result = pipeline(source, output_type="pil")
        assert isinstance(result.images, list)
        assert len(result.images) == 1
        assert isinstance(result.images[0], Image.Image)

    def test_batch_inference(self):
        pipeline = self._make_pipeline()
        source = torch.randn(2, 3, 64, 64)
        result = pipeline(source, output_type="pt")
        assert result.images.shape == (2, 3, 64, 64)


# ====================================================================
# Inference (Translator) tests
# ====================================================================


class TestCUTTranslator:
    """Tests for CUTTranslator."""

    def test_predict_returns_pil(self):
        gen = CUTResNetGenerator(
            in_channels=3, out_channels=3, base_filters=16,
            n_blocks=2, no_antialias=True, no_antialias_up=True,
        )
        translator = CUTTranslator(gen, device="cpu", image_size=64)
        img = Image.new("RGB", (128, 128))
        result = translator.predict(img)
        assert isinstance(result, Image.Image)

    def test_predict_batch(self):
        gen = CUTResNetGenerator(
            in_channels=3, out_channels=3, base_filters=16,
            n_blocks=2, no_antialias=True, no_antialias_up=True,
        )
        translator = CUTTranslator(gen, device="cpu", image_size=64)
        imgs = [Image.new("RGB", (128, 128)) for _ in range(3)]
        results = translator.predict_batch(imgs)
        assert len(results) == 3
        assert all(isinstance(r, Image.Image) for r in results)

    def test_predict_file(self, tmp_path):
        gen = CUTResNetGenerator(
            in_channels=3, out_channels=3, base_filters=16,
            n_blocks=2, no_antialias=True, no_antialias_up=True,
        )
        translator = CUTTranslator(gen, device="cpu", image_size=64)
        input_path = tmp_path / "input.png"
        output_path = tmp_path / "output.png"
        Image.new("RGB", (128, 128)).save(input_path)
        translator.predict_file(input_path, output_path)
        assert output_path.exists()
        result = Image.open(output_path)
        assert result.mode == "RGB"


# ====================================================================
# State-dict compatibility test
# ====================================================================


class TestCheckpointCompatibility:
    """Verify that state dict keys match the original CUT ResnetGenerator."""

    def test_state_dict_keys_match_original_pattern(self):
        """The new generator's state_dict keys should start with 'model.'
        matching the original CUT ResnetGenerator structure."""
        gen = CUTResNetGenerator(
            in_channels=3, out_channels=3, base_filters=64,
            n_blocks=9, no_antialias=False, no_antialias_up=False,
        )
        keys = list(gen.state_dict().keys())
        assert len(keys) > 0
        assert all(k.startswith("model.") for k in keys)

    def test_round_trip_save_load(self, tmp_path):
        """Generator can save and reload its state dict."""
        gen = CUTResNetGenerator(
            in_channels=3, out_channels=3, base_filters=16,
            n_blocks=2, no_antialias=True, no_antialias_up=True,
        )
        path = tmp_path / "test_gen.pth"
        torch.save(gen.state_dict(), path)

        gen2 = CUTResNetGenerator(
            in_channels=3, out_channels=3, base_filters=16,
            n_blocks=2, no_antialias=True, no_antialias_up=True,
        )
        gen2.load_state_dict(torch.load(path, weights_only=True))

        x = torch.randn(1, 3, 64, 64)
        gen.eval()
        gen2.eval()
        with torch.no_grad():
            assert torch.allclose(gen(x), gen2(x))
