import onnxruntime as rt
import numpy as np
import logging

logger = logging.getLogger(__name__)
providers=["CPUExecutionProvider"]

# --- Model harness wrapping the model in the contextual logic: loading onnx model, preparing input, calling inference session and interpreting the output ---

class AcousticModelProcessor:
    def __init__(self, onnx_path: str): # initialize instance taking in model from onnx_path
        self.sess = rt.InferenceSession(onnx_path, providers=providers) #initializes Inference Session for predicitions using onnx runtime and taking in model from onnx_path; explicitly stating default providers to emphasize intention

        self.input_name = self.sess.get_inputs()[0].name #returns a list of input objects (each an onnxruntime.NodeArg). Each of those has a .name attribute — a string matching the input tensor name defined when the model was exported.

        self.output_names = [output.name for output in self.sess.get_outputs()] # With the BAPE model, there are 2 output features to store => store the name for each feature in an array
        
        logger.info("Model initialized successfully.")
        logger.info("Input Name: %s, Output Names: %s", self.input_name, self.output_names)

    def run_inference(self, preprocessed_spectogram: np.ndarray) -> dict: #after model and inference session are initialized, define input_feed, a dictionary with spectrogram inputs
        """Runs the ONNX inference session and returns a dictionary of all model outputs."""
        input_feed = {self.input_name: preprocessed_spectogram} 
        # BAPE model generates multiple outputs: 
            # N `latent` vectors of shape `(N, 1024)` – The acoustic fingerprint
            # quantiles which describe uncertainty in the fingerprint
            # estimated_params in a 7 x 3 Matrix (7 octave bands, for each an estimate + an upper and lower end for each estimate describing the confidence interval) 
        all_outputs = self.sess.run(self.output_names, input_feed) 
        results = {
            name: array for name, 
            array in zip(self.output_names, all_outputs)
                         }
        
        return results
    