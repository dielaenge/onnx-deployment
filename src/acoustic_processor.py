import onnxruntime as rt
import numpy as np
import librosa

TARGET_SR = 16000 # target sample rate – placeholder value but a common one


# --- Prepare data for model input ---

def load_and_preprocess_audio(audio_path: str) -> np.ndarray: # the load_and_preprocess_audio function takes in audio_path, which will be an argument entered at function call, should be a string and expects an np.ndarray as a result (these are hints and not enforced)
    """Loads, resamples, and prepares audio data for ONNX input.""" #docstring for documentation and tools like help()
    print(f"Loading audio data from {audio_path}…")

    audio_data, current_sr = librosa.load( # tuple unpacking: the librosa.load function produces two values, the audio data (NumPy array containing the audio time series) and current sample rate, based on the load arguments…
        audio_path, # input file path
        sr=TARGET_SR, #Librosa will resample to that rate automatically, so current_sr will always equal TARGET_SR; this saves memory and additional steps
        mono=True #transform to mono
    )

    if audio_data.dtype != np.float32: # if audio data isn't a float32 format
        audio_data = audio_data.astype(np.float32) # convert data to float32 format

    audio_data_batched = np.expand_dims(audio_data, axis=0) # expand shape of librosa.load() output to have a second dimension for batch size, starting at position 0, required for processing – shape was (N,) but ONNX expects (1, N) shape

    print(f"Preprocessed audio shape: {audio_data_batched.shape}")
    return audio_data_batched


# --- Model harness wrapping the model in the contextual logic: loading onnx model, preparing input, calling inference session and interpreting the output ---

class AcousticModelProcessor:
    def __init__(self, onnx_path: str): # initialize instance taking in model from onnx_path
        self.sess = rt.InferenceSession(onnx_path) #initializes Inference Session to make predicitions using onnx runtime and taking in model from onnx_path

        self.input_name = self.sess.get_inputs()[0].name #returns a list of input objects (each an onnxruntime.NodeArg). Each of those has a .name attribute — a string matching the input tensor name defined when the model was exported.
        self.output_name = self.sess.get_outputs()[0].name # same as above but for output tensors

        print(f"Model initialized. Input Name: {self.input_name}, Output Name: {self.output_name}") #Update user on model initialization and print input_name: output_name list for reference

    def generate_vector(self, preprocessed_audio: np.ndarray) -> np.ndarray: #after model and inference session are ready can return their inputs and outputs, a function to define the vector is set up which takes in the preprocessed audio from the model
        """Runs the ONNX inference session."""

        input_feed = {self.input_name: preprocessed_audio} #creates a dictionary called input_feed required to run the InferenceSession
        result = self.sess.run([self.output_name], input_feed) #compute the vector, will be a list with one NumPy array element per output name provided (here only one output name)

        return result[0] # our batch has a size of 1, therefor returning the first (and only) vector is enough

# --- Test Function: Bring together the components ---

def test_processor(onnx_model_path: str, audio_file_path: str):
    try :
        # load the model harness
        processor = AcousticModelProcessor(onnx_model_path)

        #prepare the audio
        preprocessed_audio = load_and_preprocess_audio(audio_file_path)

        #run inference
        acoustic_vector = processor.generate_vector(preprocessed_audio)

        print("-" * 30) # line
        print("Inference successful!")
        print(f"Output vector shape: {acoustic_vector.shape}")
        print(f"Data type: {acoustic_vector.dtype}")
        print(f"First 5 elements: {acoustic_vector[0][:5]}")

    except Exception as e :
        print(f"\nError running inference: {e}")
        print("If trying with real model, check input shape and data type requirements!")

if __name__ == "__main__":
# the (dummy) model has to be exported first
# also: a sample audio file is required
    DUMMY_MODEL = "dummy_acoustic_model.onnx"
    SAMPLE_AUDIO = "test_audio.wav"

    test_processor(DUMMY_MODEL, SAMPLE_AUDIO)