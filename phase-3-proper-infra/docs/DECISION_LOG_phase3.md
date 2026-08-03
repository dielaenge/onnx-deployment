# Phase 3: Production Cloud Deployment / Integrating the BAPE model

## Phase 3.1.: Integrating the speech encoder model for blind acoustice parameter estimation (BAPE)
*Before the Production Cloud deployment, I was invited to the GitHub repository of the pre-existing PyTorch research model for blind acoustic parameter estimation (BAPE).*
*Until here, I was substituting the BAPE SpeechEncoder model with a placeholder onnx file. With the new input, the primary challenge, before creating the cloud infrastructure, was to productionize the model which was provided as a .pth weights file and a complex training repository. Exporting the model to the onnx format and making it suitable for direct deployment was a detour before working on the cloud deployment.*

This detour involved three key MLOps stages:

### 1. Model Onboarding & Conversion:
I performed a static analysis of the repository, using the `Hydra` (`.yaml`) configuration files to reverse-engineer the model's architecture and its precise data requirements. This investigation revealed that the `SpeechEncoder` model expected a 4D tensor representing a Mel Spectrogram with specific parameters (`n_mels=16`, `trunc=2000`, etc.). I then wrote a dedicated `exporter.py` script to programmatically reconstruct the model's architecture, load the pre-trained weights from the `.pth` file, and perform a formal conversion to the ONNX format. This resulted in a self-contained, deployable `speech_encoder.onnx` artifact.

### 2. Application & Preprocessing Refactoring:
I refactored my existing FastAPI application to support the new model. The core task was replacing the simplistic audio preprocessing with a new pipeline inside `audio_processor.py`. This new pipeline replicates the exact Mel Spectrogram transformation from the BAPE repository, including the 2D-to-4D tensor expansion (`[H, W] -> [N, C, H, W]`) to conform to the model's required input shape.

### 3. API Contract Enhancement:
Finally, I updated the `AcousticModelProcessor` to handle the model's multiple output tensors (`latent` and `latent_weights`/two more optional outputs not implemented yet). I enhanced the API endpoint by improving the JSON response to be more self-documenting and information rich. Instead of a simple vector, the API now provides a structured object containing metadata and both the primary `estimated_parameters` and the secondary `attention_weights`, giving the end-user more insight.

## Phase 3.2.: Sketching the cloud deployment