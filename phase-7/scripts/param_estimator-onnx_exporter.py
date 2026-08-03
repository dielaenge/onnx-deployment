import sys
from pathlib import Path
from datetime import datetime
import hydra
from omegaconf import DictConfig, OmegaConf
from hydra.utils import to_absolute_path, instantiate
import logging

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Path logic ---
# Get directory of this script
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
logger.debug("Exporter script running from %s.", PROJECT_ROOT)


# app-specific imports
import librosa
import torch
import torch.nn as nn
import numpy as np

# imports from local modules
from src.util.signals import MelSpectrogram

# Note: paths and model configs are provided via Hydra config (`conf/exporter.yaml`).

# Reference arrays removed; exporter now requires an external `.pt` reference file (cfg.output_tuple)

timestamp = datetime.now().strftime(f"%Y-%m-%d_%H-%M-%S")


@hydra.main(config_path="../conf", config_name="exporter", version_base=None)
def main(cfg: DictConfig) -> None:
    logger.info("Step 1. Resolve config paths.")
    # Resolve configured absolute paths
    cfg_ref_audio = to_absolute_path(cfg.ref_audio)
    cfg_output_tuple = to_absolute_path(cfg.output_tuple)

    # 1. Load run config
    run_cfg_path = to_absolute_path(cfg.run_cfg)
    logger.info("Step 2. Loading model config from %s", run_cfg_path)
    run_cfg = OmegaConf.load(run_cfg_path)

    # Resolve param name and setup paths
    param_name = run_cfg.get("target", run_cfg.get("param", "unknown")).upper()
    weights_path = PROJECT_ROOT / cfg.model_weights

    EXPORTED_ONNX_PATH = PROJECT_ROOT / cfg.export_dir / f"{param_name.lower()}_bape_{weights_path.parent.name}.onnx"

    # 2. Instantiate base model and wrapper
    logger.info("Step 3. Instantiating base_model from run_config...")
    base_model = instantiate(run_cfg.model)

    class ExportWrapper(nn.Module):
        def __init__(self, base):
            super().__init__()
            self.base = base

        def forward(self, x):
            if getattr(self.base, "is_vae", False):
                latents = self.base.encoder.encode(x)[0].flatten(start_dim=1)
            else:
                latents = self.base.encoder(x)[0]
            params, quantiles = self.base(x)
            return latents, params, quantiles

    param_estimator_model = ExportWrapper(base_model)
    logger.info("PyTorch model wrapped as `param_estimator_model`.\n\n")

    # 3. Load weights into model
    logger.info("Step 4: Loading pre-trained weights from %s", weights_path)
    state_dict = torch.load(weights_path, map_location="cpu")
    logger.debug("Keys loaded in state_dict: %s", state_dict.keys())
    base_model.load_state_dict(state_dict, strict=True)
    logger.info("Weights loaded to param_estimator_model.")

    param_estimator_model.eval()
    logger.info("Model set to evaluation mode.\n\n")

    # 4. Prepare input for onnx export
    logger.info("Step 5: Prepare input for onnx export.")
    logger.info("Instantiating MelSpectrogram object as `preprocessor`…")

    preprocessor = MelSpectrogram(
        sr=16000,
        n_fft=64,
        hop_size=32,
        n_mels=16,
        fmin=20,
        fmax=8000,
        power=2.0,
        log_mag=True,
        trunc=None,
    )

    logger.info("…done. Loading reference audio…")
    ref_audio, _ = librosa.load(cfg_ref_audio, sr=16000)
    logger.info(
        "…done. Reference audio loaded from %s with shape %d. Transforming to MelSpectrogram…",
        cfg_ref_audio,
        ref_audio.shape[0],
    )

    preprocessed_2d_tensor = preprocessor(ref_audio)
    logger.info(
        "Transformed ref_audio to 2D Spectrogram with shape: %s. Standardizing…",
        preprocessed_2d_tensor.shape,
    )
    preprocessed_2d_tensor = (
        preprocessed_2d_tensor - preprocessed_2d_tensor.mean()
    ) / (preprocessed_2d_tensor.std() + 1e-8)
    logger.info("…done. Adding Dimensions…")

    final_4d_tensor = preprocessed_2d_tensor.unsqueeze(0).unsqueeze(0)
    logger.info(
        "…done. Input ready for onnx export. Shape is %s",
        final_4d_tensor.shape,
    )

    # 5. Load reference outputs from provided .pt file (used for unit test)
    try:
        ref_obj = torch.load(cfg_output_tuple, map_location="cpu")
        logger.info("Loaded reference output file %s", cfg_output_tuple)
        # expecting a tuple of (output, quantiles, hard-coded for now)
        ref_output = ref_obj[0]
        ref_quantiles = ref_obj[1]
    except Exception as e:
        logger.error("Failed to load reference output %s: %s", cfg_output_tuple, e)
        ref_obj = None

    def _to_np(x):
        if isinstance(x, torch.Tensor):
            return x.cpu().numpy().flatten()
        if isinstance(x, np.ndarray):
            return x.flatten()
        if isinstance(x, (list, tuple)):
            return np.array(x).flatten()
        return np.array([x]).flatten()

    # 6. --- THE SELF-TEST & EXPORT ---
    with torch.no_grad():
        z, output, quantiles = param_estimator_model(final_4d_tensor)

        # compare output to ref output
        if ref_obj is not None:
            output_np = _to_np(output)
            ref_output_np = _to_np(ref_output)
            quantiles_np = _to_np(quantiles)
            ref_quantiles_np = _to_np(ref_quantiles)

            output_close = np.allclose(output_np, ref_output_np, atol=cfg.tolerance)
            quantiles_close = np.allclose(
                quantiles_np, ref_quantiles_np, atol=cfg.tolerance
            )

            if output_close and quantiles_close:
                logger.info(
                    "Self-test PASSED: Model outputs are close to reference outputs within tolerance of %s.",
                    cfg.tolerance,
                )
                should_export = True
            else:
                logger.error(
                    "Self-test FAILED: Model outputs differ from reference outputs beyond tolerance of %s.",
                    cfg.tolerance,
                )
                logger.debug("Output: %s", output_np)
                logger.debug("Reference Output: %s", ref_output_np)
                logger.debug("Quantiles: %s", quantiles_np)
                logger.debug("Reference Quantiles: %s", ref_quantiles_np)
                should_export = False
        else:
            logger.warning(
                "No reference output available. Skipping self-test and proceeding with export."
            )
            should_export = True

        if should_export:
            logger.info("Starting ONNX export to %s\n\n\n", EXPORTED_ONNX_PATH)

            torch.onnx.export(
                param_estimator_model,
                final_4d_tensor,
                EXPORTED_ONNX_PATH,
                input_names=["input_spectrogram"],
                output_names=["latents", "params", "quantiles"],
                opset_version=18,
                dynamic_axes={
                    "input_spectrogram": {0: "batch_size"},
                    "latents": {0: "batch_size"},
                    "params": {0: "batch_size"},
                    "quantiles": {0: "batch_size"},
                },
                dynamo=True,
                report=False,
            )

            logger.info("SUCCESS: ONNX model exported to %s.", EXPORTED_ONNX_PATH)


if __name__ == "__main__":
    main()
