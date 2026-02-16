import sys
import os

import torch
import torch.nn as nn
import numpy as np
from omegaconf import OmegaConf


# Add the BAPE source root to the Python path
# Adjust the path string to match the actual directory structure relative to this script
bape_root = os.path.abspath("src/bape") 
if bape_root not in sys.path:
    sys.path.append(bape_root)

from src.util.signals import MelSpectrogram
from src.model.param_estimator import ParameterEstimator as OriginalEstimator

from src.model.speech_encoder import SpeechEncoder
from src.model.cnn2d import CNNEncoder
from src.model.seq import SequenceModel
from src.util.layers import SelfAttentionPooling
from src.model.mlp import RegressionHead

# I. Assembling the model, the architectural shell, from scratch

print("Step 1: Definining the 'Super Model' class which returns both the outputs of the speech encoder and the parameter estimator.")

print("…defining `SuperParameterEstimator` class")

class SuperParameterEstimator(OriginalEstimator):
    def __init__(
        self,
        encoder_state, # We will ignore this argument
        freeze_encoder,
        reset_encoder,
        quantiles,
        estimator,
        p_drop=0.3
    ):
        # We do NOT call super().__init__() because it has a different path logic, as it is stored in a submodule of this repo, so We initialize nn.Module directly.
        nn.Module.__init__(self)

        self._freeze_encoder = freeze_encoder

        print("Initializing SpeechEncoder manually to avoid config path issues...")
        
        # --- 1. Manually Instantiate the SpeechEncoder ---
        # First the architecture needs to be built.
        # This mimics what 'instantiate(cfg.model)' does in the `ParameterEstimator`'s `__init__` function, but without the config file -> path depencies caused complications.
        
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
    
    #we want to get the 'z' value defined in `bape/src/model/param_estimator.py`, which is the `latent` output of the speech encoder model

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
        
        #differing from the OriginalEstimator / ParameterEstimator we return 'z' (acoustic fingerprint) AND 'outputs' (params)
        return z, output, quantiles_adjusted
    
print("`SuperParameterEstimator` class defined.")

print("Step 2: Instantiating the `SuperParameterModel` class as `param_estimator_model`.")

MODEL_WEIGHTS_PATH = "src/BAPE_src/results/param/2025-11-18_21-51-21/model.pth"

param_estimator_model = SuperParameterEstimator(
    encoder_state= None, #was: 'MODEL_WEIGHTS_PATH'
    freeze_encoder= False,
    reset_encoder= False,
    quantiles= [0.05, 0.5, 0.95],
    p_drop= 0.3275,
    estimator={
        "input_dim": 1024,
        "hidden_dim": 64,
        "num_blocks": 2,
        "output_dim": 6,
        "output_act": None
        }
)
print("Model instantiated without loaded weights as `param_estimator_model`.")


# III. Load weights into model

print("Step 3: Loading pre-trained weights.")

# #load the weights file into a dict (as ONNX requires this)
state_dict = torch.load(MODEL_WEIGHTS_PATH)

# # The weights in the pth file might be nested under a key like 'model_state' or 'component_state'. Print the keys to see the structure
# print(f"Keys loaded in state_dict: {state_dict.keys()}")

# Loading the state_dict into the model. strict=True ensures only perfect matches
param_estimator_model.load_state_dict(state_dict, strict=False)
print("Weights loaded successfully.")

#set the model to evaluation mode (≠training mode)
param_estimator_model.eval()
print("Model set to evaluation mode.")



# II. Creating a representative sample tensor for the ONNX export process
# copied from previous version `exporter.py`, where further comments can be found

print("Step 3: Generating exemplary tensor for model input.")

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

print("Preprocesscor instantiated as `preprocessor`")

SAMPLE_RATE = 16000
DURATION = 4
dummy_audio = np.zeros(SAMPLE_RATE*DURATION, dtype=np.float32)
print(f"Created dummy signal with shape: {dummy_audio.shape}")

preprocessed_2d_tensor = preprocessor(dummy_audio)
print(f"Preprocessed tensor 2D-shape: {preprocessed_2d_tensor.shape}")

preprocessed_3d_tensor = preprocessed_2d_tensor.unsqueeze(0)

print(f"Final input tensor 3D-shape: {preprocessed_3d_tensor.shape}")

final_4d_tensor = preprocessed_3d_tensor.unsqueeze(1)

assert list(final_4d_tensor.shape) == [1, 1, 16, 2000]
print(f"Input tensor shape is {final_4d_tensor.shape} and should be [1, 1, 16, 2000].")


# IV. Performing the export
print("Step 4: Exporting the model to ONNX")
EXPORTED_MODEL_PATH = "super_param_estimator_opset18.onnx" 

torch.onnx.export(
    param_estimator_model,
    final_4d_tensor,
    EXPORTED_MODEL_PATH,
    input_names=['input_spectogram'],
    output_names=['latent_vector', 'estimated_params', 'quantiles'],
    opset_version=18,
    dynamic_axes={ 
        'input_spectogram': {0 : 'batch_size'},
        'latent_vector' : {0 : 'batch_size'},
        'estimated_params' : {0 : 'batch_size'},
        'quantiles' : {0 : 'batch_size'}
    # Python will return an information about the more modern approach: 
    # dynamic_shapes = {
    #    'x': {0:torch.export.Dim("batch_size")}
    #} 
    },
    dynamo=False
)

print(f"SUCCESS: Super Model exported to {EXPORTED_MODEL_PATH}.")