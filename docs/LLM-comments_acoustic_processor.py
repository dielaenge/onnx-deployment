"""
acoustic_processor.py
---------------------

A small utility module that:
1. Loads and preprocesses audio data for ONNX model input.
2. Wraps an ONNX model in a simple processor class.
3. Demonstrates inference with a dummy or real acoustic model.
"""

import onnxruntime as rt
import numpy as np
import librosa


# --- Configuration ------------------------------------------------------------

TARGET_SR = 16000  # Target sample rate in Hz (16 kHz is a common standard)


# --- Audio Preprocessing ------------------------------------------------------

def load_and_preprocess_audio(audio_path: str) -> np.ndarray:
    """
    Load, resample, and prepare audio data for ONNX input.

    Args:
        audio_path (str): Path to the input audio file.

    Returns:
        np.ndarray: Preprocessed audio array of shape (1, N),
                    where N = number of samples.
    """
    print(f"Loading audio from: {audio_path}")

    # 1. Load and resample to target rate; ensure mono
    audio_data, current_sr = librosa.load(
        audio_path,
        sr=TARGET_SR,
        mono=True
    )

    # 2. Convert to float32 if needed
    if audio_data.dtype != np.float32:
        audio_data = audio_data.astype(np.float32)

    # 3. Add batch dimension: (N,) -> (1, N)
    audio_data_batched = np.expand_dims(audio_data, axis=0)

    print(f"Preprocessed audio shape: {audio_data_batched.shape}")
    return audio_data_batched


# --- Model Harness ------------------------------------------------------------

class AcousticModelProcessor:
    """
    A wrapper (harness) for running inference on an ONNX acoustic model.

    Responsibilities:
        - Load the ONNX model.
        - Retrieve input/output node names.
        - Run inference given preprocessed audio.
    """

    def __init__(self, onnx_path: str):
        """Initialize the ONNX Runtime inference session."""
        self.sess = rt.InferenceSession(onnx_path)
        self.input_name = self.sess.get_inputs()[0].name
        self.output_name = self.sess.get_outputs()[0].name

        print(f"Model initialized:")
        print(f"  Input  → {self.input_name}")
        print(f"  Output → {self.output_name}")

    def generate_vector(self, preprocessed_audio: np.ndarray) -> np.ndarray:
        """
        Run the model inference to generate an acoustic vector.

        Args:
            preprocessed_audio (np.ndarray): Audio array of shape (1, N).

        Returns:
            np.ndarray: Output vector from the model (shape depends on model).
        """
        # ONNX expects inputs as a dict: {input_name: input_tensor}
        input_feed = {self.input_name: preprocessed_audio}

        # Run inference and get outputs as NumPy arrays
        result = self.sess.run([self.output_name], input_feed)

        # Return the first (and only) output
        return result[0]


# --- Test Function ------------------------------------------------------------

def test_processor(onnx_model_path: str, audio_file_path: str):
    """
    Run a full inference test:
    - Load the model
    - Load and preprocess audio
    - Generate an output vector
    """
    try:
        # 1. Load model harness
        processor = AcousticModelProcessor(onnx_model_path)

        # 2. Prepare input audio
        preprocessed_audio = load_and_preprocess_audio(audio_file_path)

        # 3. Run inference
        acoustic_vector = processor.generate_vector(preprocessed_audio)

        print("-" * 30)
        print("Inference successful!")
        print(f"Output vector shape: {acoustic_vector.shape}")
        print(f"Data type: {acoustic_vector.dtype}")
        print(f"First 5 elements: {acoustic_vector[0][:5]}")

    except Exception as e:
        print(f"\nError running inference: {e}")
        print("If using a real model, check input shape and data type requirements.")


# --- Entry Point --------------------------------------------------------------

if __name__ == "__main__":
    # The dummy ONNX model must exist before running this script.
    # You can export it using create_dummy_model.py.
    DUMMY_MODEL = "dummy_acoustic_model.onnx"
    SAMPLE_AUDIO = "test_audio.wav"

    test_processor(DUMMY_MODEL, SAMPLE_AUDIO)
