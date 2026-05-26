import sys
from pathlib import Path
from datetime import datetime
import argparse
import logging

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format= '%(asctime)s - %(name)s %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Path logic ---
# Get directory of this script
SCRIPT_DIR = Path(__file__).resolve().parent
# Get project root director
PROJECT_ROOT = SCRIPT_DIR.parent
# Add the project root to the search path
if PROJECT_ROOT not in sys.path:
    sys.path.append(str(PROJECT_ROOT))  
logger.debug("Project root is: %s. Script running from %d.", PROJECT_ROOT, SCRIPT_DIR)
logger.debug("Script running from %s.", SCRIPT_DIR)

# app-specific imports
import librosa
import torch
import torch.nn as nn
import numpy as np
from omegaconf import OmegaConf

# imports from local modules
from scripts.bape_local.src.util.signals import MelSpectrogram
from scripts.bape_local.src.model.param_estimator import ParameterEstimator as OriginalEstimator

from scripts.bape_local.src.model.speech_encoder import SpeechEncoder
from scripts.bape_local.src.model.cnn2d import CNNEncoder
from scripts.bape_local.src.model.seq import SequenceModel
from scripts.bape_local.src.util.layers import SelfAttentionPooling
from scripts.bape_local.src.model.mlp import RegressionHead



# Define all I/O paths (bape repository must be vendored to src/bape_local)
T60_WEIGHTS_PATH = ( PROJECT_ROOT / "scripts" / "bape_local" / "weights" / "param" / "2025-11-18_17-40-57" / "model.pth" )
C50_WEIGHTS_PATH = ( PROJECT_ROOT / "scripts" / "bape_local" / "weights" / "param" / "2025-11-18_19-33-41" / "model.pth" )
ENCODER_WEIGHTS_PATH = ( PROJECT_ROOT / "scripts" / "bape_local" / "weights" / "speech_encoder" / "2025-11-03_17-27-17" /"model.pth" )

REF_AUDIO_PATH = ( PROJECT_ROOT / "src" / "wet_speech.wav" )

timestamp = datetime.now().strftime(f"%Y-%m-%d_%H-%M-%S")

def parse_args():
    parser = argparse.ArgumentParser(description="Export T60 or C50 BAPE models as ONNX.")
    parser.add_argument(
        "--param",
        choices=["T60", "C50"],
        required=True,
        help="Which parameter's estimator to export: Enter T60 or C50."
    )
    return parser.parse_args()

def main():
    args = parse_args()

# DEFINE FOR WHICH PARAM, THE MODEL EXPORT SHOULD HAPPEN
    if args.param == "T60":
        weights_path = T60_WEIGHTS_PATH
        EXPORTED_ONNX_PATH = ( PROJECT_ROOT / "app" / "models" / f"t60_bape_{timestamp}.onnx" )
        expected_reference = [0.4660, 0.5458, 0.8592]
        logger.info("Exporting ONNX model for T60 estimation to %s", EXPORTED_ONNX_PATH)
    elif args.param == "C50":
        weights_path = C50_WEIGHTS_PATH
        EXPORTED_ONNX_PATH = ( PROJECT_ROOT / "app" / "models" / f"c50_bape_{timestamp}.onnx" )
        expected_reference = None

    # I. Assembling the model, the architectural shell, from scratch
    logger.info("Step 1: Definining the 'Super Model' class which returns both the outputs of the speech encoder and the parameter estimator.")
    logger.info("…defining `SuperParameterEstimator` class")

    class SuperParameterEstimator(OriginalEstimator):
        def __init__(
            self,
            encoder_state,
            freeze_encoder,
            reset_encoder,
            quantiles,
            estimator,
            p_drop=0.3
        ):
            # We do NOT call super().__init__() because it has a different path logic, as it is stored in a submodule of this repo, so We initialize nn.Module directly.
            nn.Module.__init__(self)

            self._freeze_encoder = freeze_encoder

            logger.info("Configuring SpeechEncoder separately to avoid config path issues with hydra...")
            
            # Instantiate the SpeechEncoder
            
            # Create the Front End (CNN)
            # Values taken from typical BAPE config (16kHz, 16 mels)
            front_end = CNNEncoder(
                in_channels=1, channels=16, multipliers=[1, 2, 2, 4, 4],
                kernel_sizes=[[1, 7], [1, 7], [3, 7], [3, 7], [3, 7]],
                strides=[[1, 1], [1, 1], [1, 1], [1, 1], [1, 1]],
                factors=[[1, 1], [1, 2], [1, 2], [2, 2], [2, 2]],
                pads=[[0, 0], [0, 0], [0, 0], [0, 0], [0, 0]],
                num_blocks=[1, 1, 1, 1, 1]
            )
            
            # Create the Sequence Model
            sequence_model = SequenceModel(
                d_model=256, nhead=4, dim_feedforward=512, num_layers=2,
                dropout=0.1, d_out=1024, act_out="tanh", att_pool=True, film=None
            )
            
            # Create the Encoder
            self.encoder = SpeechEncoder(front_end=front_end, sequence_model=sequence_model)
            
            if encoder_state is not None:
                logger.info("Loading Encoder weights from %s\n\n", encoder_state)
                
                # Load the dictionary
                state_dict = torch.load(encoder_state, map_location="cpu")
                
                logger.info("----WEIGHTS FILE KEY AUDIT ----")
                for key in list(state_dict.keys())[:5]:
                    logger.info("File Key: %s", key)

                # Load state_dict into encoder submodule
                # strict=False allows ignoring unexpected "error_model" and "quantile" keys
                missing_keys, unexpected_keys = self.encoder.load_state_dict(state_dict, strict=False)
                logger.info("KEY AUDIT RESULT: %s missing keys, %d unexpected keys.", len(missing_keys), len(unexpected_keys))
                if missing_keys:
                    logger.info("MISSING FROM ENCODER: %s...\n", missing_keys[:3]) # Print first 3
            
            self.is_vae = False

            # Initialize Regression Heads (Copied from original __init__)
            if quantiles is None:
                self.num_heads = 1
                self.conformalize = False
                self.heads = nn.ModuleList([RegressionHead(**estimator)])
            else:
                self.conformalize = True
                self.num_heads = len(quantiles)
                # Note: DictConfig vs Dict. We assume 'estimator' is a standard dict here.
                # We use standard kwargs unpacking (**estimator).
                self.heads = nn.ModuleList(
                    [RegressionHead(**estimator) for _ in range(self.num_heads)]
                )
                self.register_buffer(
                    "quantile_adjustment", torch.zeros(estimator['output_dim'])
                )

            self.dropout = nn.Dropout(p_drop)
            logger.info("SuperParameterEstimator initialized successfully.")
        
        def forward(self, x):
        
        #we want to get the 'z' value, which is the `latent` output of the speech encoder model

            # Run the internal SpeechEncoder to get the latent vector 'z'
            if self._freeze_encoder:
                with torch.no_grad():
                    if self.is_vae:
                        z = self.encoder.encode(x)[0].flatten(start_dim=1)
                    else:
                        z = self.encoder(x)[0]
            else:
                if self.is_vae:
                    z = self.encoder.encode(x)[0].flatten(start_dim=1)
                else:
                    z = self.encoder(x)[0]

            z_dropped = self.dropout(z)
            
            # run the regression heads to get the parameters
            output = torch.stack([head(z_dropped) for head in self.heads], dim=2)

            if self.conformalize:
                # compute conformalized predictions
                quantiles_adjusted = torch.stack(
                    [
                        output[..., 0] - self.quantile_adjustment[None, :],
                        output[..., -1] + self.quantile_adjustment[None, :],
                    ],
                    dim=2,
                )
            else:
                quantiles_adjusted = None
            
            #differing from the OriginalEstimator / ParameterEstimator we return 'z' (latent / acoustic fingerlogger.info) AND 'outputs' (params)
            return z, output, quantiles_adjusted
        
    logger.info("`SuperParameterEstimator` class defined.\n\n")

    logger.info("Step 2: Instantiating the `SuperParameterEstimator` class as `param_estimator_model`.")

    param_estimator_model = SuperParameterEstimator(
        encoder_state= ENCODER_WEIGHTS_PATH,
        freeze_encoder= False,
        reset_encoder= False,
        quantiles= [0.05, 0.5, 0.95],
        p_drop= 0.3,
        estimator={
            "input_dim": 1024,
            "hidden_dim": 64,
            "num_blocks": 2,
            "output_dim": 7,
            "output_act": "relu"
            }
    )
    logger.info("PyTorch model instantiated with speech_encoder state from %s as `param_estimator_model`.\n\n", weights_path)


    # III. Load weights into model

    logger.info("Step 3: Loading pre-trained weights from %s", weights_path)

    # #load the weights file into a dict (as ONNX requires this)
    state_dict = torch.load(weights_path, map_location="cpu")

    # # The weights in the pth file might be nested under a key like 'model_state' or 'component_state'. Print the keys to see the structure
    logger.debug("Keys loaded in state_dict: %s", state_dict.keys())

    # Loading the state_dict into the model. strict=True ensures only perfect matches
    param_estimator_model.load_state_dict(state_dict, strict=False)
    logger.info("Weights loaded to param_estimator_model.")

    #set the model to evaluation mode (≠training mode)
    param_estimator_model.eval()
    logger.info("Model set to evaluation mode.\n\n")

    # II. Instantiate a MelSpectrogram object
    logger.info("Step 4: Prepare input for onnx export.")
    logger.info("Instantiating MelSpectrogram object as `preprocessor`…")

    preprocessor = MelSpectrogram(
    sr= 16000,
    n_fft= 64,
    hop_size= 32,
    n_mels= 16,
    fmin= 20,
    fmax= 8000,
    power= 2.0,
    log_mag= True,
    trunc= 2000
    )

    logger.info("…done. Loading reference audio…")

    ref_audio, _ = librosa.load(REF_AUDIO_PATH, sr=16000)
    logger.info("…done. Reference audio loaded from %s with shape %d. Transforming to MelSpectrogram…", REF_AUDIO_PATH, ref_audio.shape[0])

    preprocessed_2d_tensor = preprocessor(ref_audio)
    logger.info("Transformed ref_audio to 2D Spectrogram with shape: %s. Standardizing…", preprocessed_2d_tensor.shape)
    preprocessed_2d_tensor = (preprocessed_2d_tensor - preprocessed_2d_tensor.mean()) / (preprocessed_2d_tensor.std() + 1e-8)
    logger.info("…done. Adding Dimensions…")

    final_4d_tensor = preprocessed_2d_tensor.unsqueeze(0).unsqueeze(0)
    logger.info("…done. Input ready for onnx export. Shape is %s and should be [Batch = 1, Channel = 1, Height = 16, Width= 2000]. Running unit test to verify…\n", final_4d_tensor.shape)

    # --- THE SELF-TEST ---
    with torch.no_grad():
        z, output, quantiles = param_estimator_model(final_4d_tensor)
        actual_np = output[0, 0, :3].numpy()
        tolerance = 0.05
        should_export = False

        if expected_reference is not None:
            logger.info("UNIT TEST FOR T60 MODEL: COMPARING INFERENCE RESULTS OF PYTORCH MODEL AGAINST REFERENCE RESULTS")
            logger.info("EXPORTED T60 SAMPLE RESULTS: %s", actual_np)
            logger.info("EXPECTED RESULTS: %s", expected_reference)
            
            if np.allclose(actual_np, expected_reference, atol=tolerance):
                logger.info("All values within %s tolerance. T60 unit test passed.", tolerance)
                should_export = True
            
            else:
                logger.error("Output mismatch caused T60 unit test failure. Cancelling export…")

        else: 
            logger.info("Step 4: Exporting C50 model to ONNX…")
            logger.info("EXPORTED C50 SAMPLE RESULTS: %s", actual_np)
            should_export = True

        if should_export:
            logger.info("Starting ONNX export to %s\n\n\n", EXPORTED_ONNX_PATH)

            torch.onnx.export(
                param_estimator_model,
                final_4d_tensor,
                EXPORTED_ONNX_PATH,
                input_names=['input_spectrogram'],
                output_names=['latents', 'params', 'quantiles'],
                opset_version=18,
                dynamic_axes={ 
                    'input_spectrogram': {0 : 'batch_size'},
                    'latents' : {0 : 'batch_size'},
                    'params' : {0 : 'batch_size'},
                    'quantiles' : {0 : 'batch_size'}
                },
                dynamo = True,
                report = False
            )

            logger.info("SUCCESS: ONNX model exported to %s.", EXPORTED_ONNX_PATH)

if __name__ == "__main__":
    main()