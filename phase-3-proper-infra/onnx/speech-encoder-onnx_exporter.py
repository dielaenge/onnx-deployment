import torch
import numpy as np

from src.BAPE_src.signals import MelSpectrogram
from src.BAPE_src.speech_encoder import SpeechEncoder

from src.BAPE_src.cnn2d import CNNEncoder
from src.BAPE_src.seq import SequenceModel

from collections import OrderedDict



# I. Assembling the model, the architectural shell, from scratch

print("Step 1: Assembling the model architecture.")

# - instantiate all submodules,…

front_end = CNNEncoder( #config values from bape/conf/model/speech_encoder.yaml
    in_channels=1,
    channels=16,
    multipliers= [1, 2, 2, 4, 4],
    kernel_sizes= [[1, 7], [1, 7], [3, 7], [3, 7], [3, 7]],
    strides= [[1, 1], [1, 1], [1, 1], [1, 1], [1, 1]],
    factors= [[1, 1], [1, 2], [1, 2], [2, 2], [2, 2]],
    pads= [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0]],
    num_blocks= [1, 1, 1, 1, 1]
)

sequence_model = SequenceModel( #config values from bape/conf/model/speech_encoder.yaml
  d_model= 256,
  nhead= 4,
  dim_feedforward= 512,
  num_layers= 2,
  dropout= 0.1,
  d_out= 1024, # size of z_h
  act_out= "tanh",
  att_pool= True,
  film= None
)


# - …then the main module
model = SpeechEncoder(
    front_end=front_end,
    sequence_model=sequence_model
)

print("Model architecture assembled successfully.")

# - instantiate MelSpectrogram using the exact parameters (sr, n_fft, n_mels, trunc, etc.) found in bape/conf/datagen_speech.yaml.
print("Step 2: Generating exemplary tensor for model input.")
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



# II. Creating a representative sample tensor for the ONNX export process
# - create a dummy numpy tensor (use datagen_speech.yaml to get parameters)
SAMPLE_RATE = 16000
DURATION = 4
dummy_audio = np.zeros(SAMPLE_RATE*DURATION, dtype=np.float32)
print(f"Created dummy signal with shape: {dummy_audio.shape}")

# - process it with MelSpectogram to get a spectogram
preprocessed_2d_tensor = preprocessor(dummy_audio)
print(f"Preprocessed tensor 2D-shape: {preprocessed_2d_tensor.shape}")

# - augment the tensor from 2D to 3D by adding a dimension at index=0
preprocessed_3d_tensor = preprocessed_2d_tensor.unsqueeze(0)
# - check shape (1, 16, 2000)
print(f"Final input tensor 3D-shape: {preprocessed_3d_tensor.shape}")
# CNN2d expects a 4D tensor, so we have to add a dimension
final_4d_tensor = preprocessed_3d_tensor.unsqueeze(1)
# quick assertion to make sure
assert list(final_4d_tensor.shape) == [1, 1, 16, 2000]
print(f"Input tensor shape is {final_4d_tensor.shape} and should be [1, 1, 16, 2000].")



# III. Ingest pth into architectural shell
print("Step 3: Loading pre-trained weights.")

MODEL_WEIGHTS_PATH="src/BAPE_src/model.pth" #pth is a weights file

#load the weights file into a dict (as ONNX requires this??)
state_dict = torch.load(MODEL_WEIGHTS_PATH)

# The weights in the pth file might be nested under a key like 'model_state' or 'component_state'. Print the keys to see the structure
print(f"Keys loaded in state_dict: {state_dict.keys()}")

# depending on the printout the key of state_dict might need to be changed
# model_weights = state_dict['component_state'] => not necessary as keys are not nested
# model.load_state_dict(state_dict) => model keys of 'model' are different than those of model.pth
# print("Model weights loaded successfully.")

# we try to clean the keys
new_state_dict = OrderedDict()

prefix = "encoder."

for k, v in state_dict.items():
    if k.startswith(prefix):
        name = k[len(prefix):] # name is from end of prefix to end of key (=> cut off prefix)
        new_state_dict[name] = v

# keys have been cleaned and added to a new dict
# we load the cleaned dict into the model and set strict=False because pth file might contain extra weights for 'heads' and 'error_model' which we dont have
model.load_state_dict(new_state_dict, strict=False)
print("Weights remapped and loaded successfully.")

#set the model to evaluation mode (≠training mode)
model.eval()
print("Model set to evaluation mode.")

# IV. Performing the export
print("Step 4: Exporting the model to ONNX")
EXPORTED_MODEL_PATH = "speech_encoder.onnx" 

torch.onnx.export(
    model,
    final_4d_tensor,
    EXPORTED_MODEL_PATH,
    input_names=['input_spectogram'],
    output_names=['latent', 'latent_weights'],
    #opset_version=18, #left undefined to use deafult/recommended
    dynamic_axes={ 
        'input_spectogram': {0 : 'batch_size'},
        'latent' : {0 : 'batch_size'}
    # Python will return an information about the more modern approach: 
    # dynamic_shapes = {
    #    'x': {0:torch.export.Dim("batch_size")}
    #} 
    },
    dynamo=False
)

print(f"SUCCESS: Model has been exported to {EXPORTED_MODEL_PATH}.")
print("Next step: Use the model in the FastAPI wrapper")