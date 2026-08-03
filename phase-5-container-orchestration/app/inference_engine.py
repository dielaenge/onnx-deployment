import onnxruntime as ort
import numpy as np
import logging

logger = logging.getLogger(__name__)
providers=["CPUExecutionProvider"]

# --- Model harness wrapping the model in the contextual logic: loading onnx model, preparing input, calling inference session and interpreting the output ---

class AcousticModelProcessor:
    def __init__(self, onnx_path: str): # initialize instance taking in model from onnx_path
        self.sess = ort.InferenceSession(onnx_path, providers=providers) #initializes Inference Session taking in model from onnx_path; explicitly stating default providers to emphasize intention

        self.input_name = self.sess.get_inputs()[0].name #returns a list of input objects (each an onnxruntime.NodeArg) with a .name attribute at index [0] — a string matching the input tensor name defined when the model was exported.

        self.output_names = [output.name for output in self.sess.get_outputs()] # The SuperParamEstimator returns 3 output values: latents, params and quantiles => store the name for each feature in an array
        
        logger.info("Model initialized successfully.")
        logger.info("Input Name: %s, Output Names: %s", self.input_name, self.output_names)

    def run_inference(self, batch_inference_input: np.ndarray) -> dict: #input_feed, a dictionary with spectrogram inputs
        """
        Runs ONNX inference iteratively over a dynamically sized batch of spectrograms.
        Because the exported ONNX Transformer graph requires a strict static batch size of 1, this function slices the[N, 1, 16, 2000] input into individual [1, 1, 16, 2000] arrays, processes them sequentially, and concatenates the results back into a batched format.
        """
        
        all_latents, all_params, all_quantiles = [],[],[]

        for i in range(batch_inference_input.shape[0]):
            single_input = batch_inference_input[i:i+1]
            outputs = self.sess.run(self.output_names, {self.input_name: single_input})
            all_latents.append(outputs[0])
            all_params.append(outputs[1])
            all_quantiles.append(outputs[2])
        
        return {
            self.output_names[0]: np.concatenate(all_latents, axis=0),
            self.output_names[1]: np.concatenate(all_params, axis=0),
            self.output_names[2]: np.concatenate(all_quantiles, axis=0)
}
    