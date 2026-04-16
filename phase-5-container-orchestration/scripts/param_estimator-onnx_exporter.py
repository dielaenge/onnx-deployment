import sys
import os
from pathlib import Path
from datetime import datetime

import librosa
import torch
import torch.nn as nn
import numpy as np
from omegaconf import OmegaConf

# --- Path logic ---
# Get directory of this script
SCRIPT_DIR = Path(__file__).resolve().parent

# Get project root director
PROJECT_ROOT = SCRIPT_DIR.parent

# Add the project root to the search path
if PROJECT_ROOT not in sys.path:
    sys.path.append(str(PROJECT_ROOT))  
print(f"DEBUG: Project root is: {PROJECT_ROOT}.\nScript running from {SCRIPT_DIR}.\n")
print(f"DEBUG: Script running from {SCRIPT_DIR}.\n")

from scripts.bape_local.src.util.signals import MelSpectrogram
from scripts.bape_local.src.model.param_estimator import ParameterEstimator as OriginalEstimator

from scripts.bape_local.src.model.speech_encoder import SpeechEncoder
from scripts.bape_local.src.model.cnn2d import CNNEncoder
from scripts.bape_local.src.model.seq import SequenceModel
from scripts.bape_local.src.util.layers import SelfAttentionPooling
from scripts.bape_local.src.model.mlp import RegressionHead

# Define all I/O paths (bape repository must be vendored to src/bape_local)
ESTIMATOR_WEIGHTS_PATH = ( PROJECT_ROOT / "scripts" / "bape_local" / "weights" / "param" / "2025-11-18_17-40-57" / "model.pth" )

ENCODER_WEIGHTS_PATH = ( PROJECT_ROOT / "scripts" / "bape_local" / "weights" / "speech_encoder" / "2025-11-03_17-27-17" /"model.pth" )

REF_AUDIO_PATH = ( PROJECT_ROOT / "src" / "wet_speech.wav" )

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
EXPORTED_ONNX_PATH = ( PROJECT_ROOT / "app" / "models" / f"bape_{timestamp}.onnx" )



# I. Assembling the model, the architectural shell, from scratch

print("Step 1: Definining the 'Super Model' class which returns both the outputs of the speech encoder and the parameter estimator.")

print("…defining `SuperParameterEstimator` class")

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

        print("Configuring SpeechEncoder separately to avoid config path issues with hydra...")
        
        # --- 1. Manually Instantiate the SpeechEncoder ---
        # First the architecture needs to be built.
        
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
            print(f"Loading Encoder weights from {encoder_state}")
            
            # Load the dictionary
            state_dict = torch.load(encoder_state, map_location="cpu")
            
            print("\n----WEIGHTS FILE KEY AUDIT ----")
            for key in list(state_dict.keys())[:5]:
                print(f"File Key: {key}")
            print("-------------------------------\n")

            # Load it into the encoder submodule
            # strict=False allows ignoring unexpected "error_model" and "quantile" keys
            missing_keys, unexpected_keys = self.encoder.load_state_dict(state_dict, strict=False)
            print(f"\nKEY AUDIT RESULT: {len(missing_keys)} missing keys, {len(unexpected_keys)} unexpected keys.")
            if missing_keys:
                print(f"MISSING FROM ENCODER: {missing_keys[:3]}...\n") # Print first 3
        
        self.is_vae = False

        # --- 2. Initialize Regression Heads (Copied from original __init__) ---
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
        print("SuperParameterEstimator initialized successfully.")
    
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
        
        #differing from the OriginalEstimator / ParameterEstimator we return 'z' (latent / acoustic fingerprint) AND 'outputs' (params)
        return z, output, quantiles_adjusted
    
print("`SuperParameterEstimator` class defined.")

print("\nStep 2: Instantiating the `SuperParameterEstimator` class as `param_estimator_model`.")

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
print(f"\nPyTorch model instantiated with speech_encoder state from {ENCODER_WEIGHTS_PATH} as `param_estimator_model`.")


# III. Load weights into model

print(f"\n\nStep 3: Loading pre-trained weights from {ESTIMATOR_WEIGHTS_PATH}")

# #load the weights file into a dict (as ONNX requires this)
state_dict = torch.load(ESTIMATOR_WEIGHTS_PATH, map_location="cpu")

# # The weights in the pth file might be nested under a key like 'model_state' or 'component_state'. Print the keys to see the structure
# print(f"Keys loaded in state_dict: {state_dict.keys()}")

# Loading the state_dict into the model. strict=True ensures only perfect matches
param_estimator_model.load_state_dict(state_dict, strict=False)
print("Done.")

# TBD: MISSING ERROR STATEMENTS

#set the model to evaluation mode (≠training mode)
param_estimator_model.eval()
print("\nModel set to evaluation mode.")

# II. Instantiate a MelSpectrogram object

print(f"\n\nStep 4: Prepare input for onnx export.")
print("Instantiating MelSpectrogram object `preprocessor`…")

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

print("…done.\nLoading reference audio…")

ref_audio, _ = librosa.load(REF_AUDIO_PATH, sr=16000)
print(f"…done.\nReference audio loaded from {REF_AUDIO_PATH} with shape {ref_audio.shape}.\nTransforming to MelSpectrogram…")

preprocessed_2d_tensor = preprocessor(ref_audio)
print(f"Transformed ref_audio to 2D Spectrogram with shape: {preprocessed_2d_tensor.shape}.\nStandardizing…")
preprocessed_2d_tensor = (preprocessed_2d_tensor - preprocessed_2d_tensor.mean()) / (preprocessed_2d_tensor.std() + 1e-8)
print(f"…done.\nAdding Dimensions…")

final_4d_tensor = preprocessed_2d_tensor.unsqueeze(0).unsqueeze(0)
print(f"…done.\nInput ready for onnx export. Shape is {final_4d_tensor.shape} and should be [Batch = 1, Channel = 1, Height = 16, Width= 2000].\nRunning unit test to verify…\n")

# --- THE SELF-TEST ---
with torch.no_grad():
    z, output, quantiles = param_estimator_model(final_4d_tensor)

    reference = [0.4660, 0.5458, 0.8592]
    actual = output[0, 0, :3]
    actual_np = actual.numpy()

    tolerance = 0.05

    print("\n--- UNIT TEST: COMPARING INFERENCE RESULTS OF PYTORCH MODEL AGAINST REFERENCE RESULTS---")
    print(f"EXPORT: {[f'{value:.4f}' for value in output[0, 0, :3]]}")
    print("REFERENCE: [0.4660, 0.5458, 0.8592]")
    
    if np.allclose(actual_np, reference, atol=tolerance, rtol=0):
        print(f"All values within {tolerance} tolerance. Unit test passed.")
        print("---------------------------------------\n")

        # IV. Performing the export
        print("Step 4: Exporting model to ONNX…")

        torch.onnx.export(
            param_estimator_model,
            final_4d_tensor,
            EXPORTED_ONNX_PATH,
            input_names=['input_spectrogram'],
            output_names=['latents', 'params', 'quantiles'],
            opset_version=17,
            dynamic_axes={ 
                'input_spectrogram': {0 : 'batch_size'},
                'latents' : {0 : 'batch_size'},
                'params' : {0 : 'batch_size'},
                'quantiles' : {0 : 'batch_size'}
            },
            dynamo = True,
            report = True
        )

        print(f"SUCCESS: Super Model exported to {EXPORTED_ONNX_PATH}.")
    else:
        print("Unit test failed: Model output not within tolerance.\nExport cancelled.")
        print("---------------------------------------\n")
    


