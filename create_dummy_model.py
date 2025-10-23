import torch
import torch.nn as nn # PyTorch provided neural network module
import numpy as np #for numerical operations

# --- Config ---

ACOUSTIC_VECTOR_DIM = 512 # D: dimensions of processed audio
MOCK_INPUT_LENGTH = 16000 * 5 # N: 5 seconds of audio at 16kHz

class DummyAcousticModel(nn.Module): # Create a DummyAcousticModel class, inheriting from nn.Module
    def __init__(self, output_dim): # initialize the model; requires output dimension, later ACOUSTIC_VECTOR_DIM is used
        super().__init__() # call the parent class (nn.Module) constructor
        self.output_dim = output_dim # make output dimension available through the DummyAcosuticModel instance
        self.projection = nn.Linear(1, output_dim, bias=False) # create a linear layer to project input to output dimension; torch.nn.Linear(in_features=size of each input sample, out_features=size of each output sample, …)

    def forward(self, x): #each PyTorch Module requires a forward functio to define how data (x = the input tensor) flows throgh the model's layers
        pooled_value = x.mean(dim=1, keepdim=True) #defines pooled_value by calling the torch.mean fucntion on x returning the mean value of all elements in the input tensor x; dim defines the dimension(s) to reduce, keepdim defines whether the ouput tensor should have as much dimensions as the input
        output_vector = self.projection(pooled_value) #defines output_vector as the result of the pooled value going through the linear layer

        return output_vector
    

# --- Export Process ---
def export_dummy_onnx(model_path="dummy_acoustic_model.onnx"):
    model = DummyAcousticModel(ACOUSTIC_VECTOR_DIM)

    dummy_input = torch.randn(1, MOCK_INPUT_LENGTH, dtype=torch.float32) # dummy input is a tensor filled with random float32 numbers and has a shape of (1, MOCK_INPUT_LENGTH)

    # defining names for input and output nodes for ONNX runtime / crucial to identify nodes
    input_names = ["input_raw_audio"]
    output_names = ["output_acoustic_vector"]

    #defining the export format of the model
    torch.onnx.export(
        model,
        dummy_input,
        model_path,
        export_params=True, # if weigths should be exported
        #opset_version=14 # The version of the default (ai.onnx) opset to target. None to use recommended version.
        input_names=input_names,
        output_names=output_names,
        dynamic_axes={'input_raw_audio': {1: 'time_steps'}} #key concept to handle variable file lengths – map variable time axises of input files to model shape
    )

    print(f"Dummy ONNX model exported successfully to {model_path}")
    print(f"Model expects input shape (1,N) and outputs (1, {ACOUSTIC_VECTOR_DIM}).")

if __name__ == "__main__":
    export_dummy_onnx()

