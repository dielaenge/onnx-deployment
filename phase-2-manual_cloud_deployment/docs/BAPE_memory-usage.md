Line #    Mem usage    Increment  Occurrences   Line Contents
=============================================================
    22    155.3 MiB    155.3 MiB           1       @profile
    23                                             def generate_vector(self, preprocessed_spectogram: np.ndarray) -> dict: #after model and inference session are initialized, a function to define the vector is set up which takes in the preprocessed audio from the model
    24                                                 """Runs the ONNX inference session and returns a dictionary of all model outputs."""
    25                                         
    26    155.3 MiB      0.0 MiB           1           input_feed = {self.input_name: preprocessed_spectogram} #creates a dictionary called input_feed required to run the InferenceSession
    27    176.2 MiB     21.0 MiB           1           all_outputs = self.sess.run(self.output_names, input_feed) #the BAPE model generates a set of outputs from a single input: one `latent` vector of shape `(1, 1024)` and `latent_weights` vector of shape `(1, 256)`
    28    176.2 MiB      0.0 MiB           8           results = {
    29    176.2 MiB      0.0 MiB           4               name: array for name, 
    30    176.2 MiB      0.0 MiB           3               array in zip(self.output_names, all_outputs)
    31                                                                  }
    32                                                 
    33    176.2 MiB      0.0 MiB           1           return results