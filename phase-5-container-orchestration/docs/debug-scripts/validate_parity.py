import librosa
import onnxruntime
import torch

from src.BAPE_src.param_estimator import ParameterEstimator
from src.util.signals import MelSpectrogram

# Load Speech Encoder State
estimator_state = torch.load("src/BAPE_src/results/param/2025-11-18_17-40-57/model.pth" map_location="cpu")

# Create ParameterEstimator Object
# ALL config values from `results/speech_encoder/2025-11-03_17-27-17/config.yaml``
param_estimator_model = ParameterEstimator(
    encoder_state="src/BAPE_src/results/speech_encoder/2025-11-03_17-27-17/model.pth",
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

# load refernce audio
audio_input, _ = librosa.load("src/wet_speech.wav", sr=16000)


preprocessed_2d_tensor = preprocessor(audio_input)
print(f"Preprocessed tensor 2D-shape: {preprocessed_2d_tensor.shape}")

preprocessed_3d_tensor = preprocessed_2d_tensor.unsqueeze(0)

print(f"Input tensor 3D-shape: {preprocessed_3d_tensor.shape}")

final_4d_tensor = preprocessed_3d_tensor.unsqueeze(1)

assert list(final_4d_tensor.shape) == [1, 1, 16, 2000]
print(f"Input tensor shape is {final_4d_tensor.shape} and should be [1, 1, 16, 2000].")


param_estimator_model.load_state_dict(estimator_state, strict=True)

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

torch_outputs = param_estimator_model(final_4d_tensor)



# ---

onnx_inputs = [tensor.numpy(force=True) for tensor in preprocessed_audio_input]
print(f"Input length: {len(onnx_inputs)}")
print(f"Sample input: {onnx_inputs}")

ort_session = onnxruntime.InferenceSession(
    "onnx/super_param_estimator_opset18_2025-11-18_17-40-57.onnx", providers=["CPUExecutionProvider"]
)

# I'm really unsure about this next line. I don't unerstand the variables and methods
onnxruntime_input = {input_arg.name: input_value for input_arg, input_value in zip(ort_session.get_inputs(), onnx_inputs)}

# ONNX Runtime returns a list of outputs
onnxruntime_outputs = ort_session.run(None, onnxruntime_input)[0]

#---

assert len(torch_outputs) == len(onnxruntime_outputs)
for torch_output, onnxruntime_output in zip(torch_outputs, onnxruntime_outputs):
    torch.testing.assert_close(torch_output, torch.tensor(onnxruntime_output))

print("PyTorch and ONNX Runtime output matched!")
print(f"Output length: {len(onnxruntime_outputs)}")
print(f"Sample output: {onnxruntime_outputs}")