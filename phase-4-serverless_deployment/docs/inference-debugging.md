Mid March, at the beginning of phase 5, my collaborator checked the reference results of his training against the results of our onnx model, which differed. And since the BAPE model is deterministtic, the correct onnx export would always produce the same results for the same input.

I set up a new branch `debug/inference-sandbox` and reverted to the repo state tagged `phase-4.0-monolith` which did one shot inference. When the results were still wrong, we knew there is definitely a bug in either the preprocessing or / and the onnx export.

I wanted to retrace the data pipeline and how the input is transformed.

The pipeline I would be checking against is:

1. Upload audio file as bytes 
    `WAV/M4A` --> `bytes`
    if `M4A` --convert with `FFmpeg`--> (?)
2. Transform to floating point array with Librosa
    - `Librosa` might filter the input and skew the results
    - look up packeages used by BAPE to create array (`scipy.io.wavfile.read` or `soundfile.read`)
3. Add dimension to create 2D Spectrogram
4. Expand dims for model input
5. Run inference

Next, I would strip the preprocessing of the pipeline to check the raw model results. 
My collaborator's reference results are based on a 4 second wav file, which already comes in 16 kHz, Mono, 24 Bits per sample.

So far the app 

- checks each input if its an audio file
- `.read()`s the audio file
- runs the read audio file through the `transform_to_spectrogram()`function, which is the main preprocessing function and runs *any* audio file throuch `_normalize_audio_with_ffmpeg()`, which could introduce changes to the reference file. 
--> I should transform the reference input to a spectrogram without audio preprocessing 

I will

- create a new script `debug_inference.py`
- load the reference input with librosa without running the ffmpeg command before ≠ normalize_audio_with_ffmpeg() in audio_processor.py
- run it through the melspec_preprocessor (instance of MelSpectrogram) --> 2D spectrogram (comparison to reference?)
- expands the array to become the shape required by the generate_vector() function in api.py (1,1,16,2000)
- runs it through generate_vector() and see if same pipeline without ffmpeg creates reference results

**Result:** 
The resulting blindly estimated parameters equate to the same (wrong) results of the `phase-4.0-monolith` version of the Lambda deployment (almost, results vary by approx. +/- 0.00001, I assume this is cause by the different compute environments).

It follows:
  - ffmpeg normalization not causal to the parameter drift
  - bug must be in
    - exporter script or
    - model_processor
      - I asked Phillip if the MelSpectrogram instance in api.py is configured correctly…
        ![MelSpectrogram Request](image.png)
      - … it was

Looking through the exporter script and hwo it imitates the original BAPE architecture several details stood out:

- the SuperParameterEstimator instance `param_estimator_model` ignored the `encoder_state` argument which should load the `speech_encoder` weights
- in the `config.yaml` of the training results the values differed slightly from the settings in the exporter script
- copying the files required for the model export from the phase 3 to phase 4 folder set off a load of path errors

After fixing these aspects the first results using the new onnx export still came out wrong, narrowing down the problem cause to the Spectrogram input resulting in the model outputs.

Using VS Code debugging console I 
- checked Min, Max and Mean values of the spectrogram my exporter script produces
- saved my spectrogram

```zsh
print(f"Max: {preprocessed_2d_tensor.max().item()}")
print(f"Min: {preprocessed_2d_tensor.min().item()}")
print(f"Mean: {preprocessed_2d_tensor.mean().item()}")
Max: 0.0
Min: -115.0830078125
Mean: -51.70022964477539

import numpy as np

np.save("david_spec.npy", preprocessed_2d_tensor.numpy())
```

I received a the spectrogram for the reference audio input and could now do some basic data analysis on it, at the same breakpoint in the debug console:

```zsh
# 1. Load reference spectrogram
ref_spec = torch.load("phase-4-serverless_deployment/src/input_spec.pt", map_location="cpu")

# 2. do the shapes match?
print(f"Reference shape: {ref_spec.shape} | David shape: {preprocessed_2d_tensor.shape}")
Reference shape: torch.Size([16, 2001]) | David shape: torch.Size([16, 2001])


# 3. Normalization test
print(f"Reference max: {ref_spec.max()} | David max: {preprocessed_2d_tensor.max()}")
Reference max: 2.207984209060669 | David max: 0.0


print(f"Reference min: {ref_spec.min()} | David min: {preprocessed_2d_tensor.min()}")
Reference min: -2.703648567199707 | David min: -115.0830078125


torch.allclose(torch.tensor(ref_spec), torch.tensor(preprocessed_2d_tensor))
<string>:1: UserWarning: To copy construct from a tensor, it is recommended to use sourceTensor.detach().clone() or sourceTensor.detach().clone().requires_grad_(True), rather than torch.tensor(sourceTensor).
False
```

So we see a difference in the order of a magnitude.


### Export refactor
I used the `ref_spec` currently loaded in the Debug Console and ran it through the model instead of our initial spectrogram.
*Debug Console for exporter script with Breakpoint after weights have been loaded and `param_estimator_model`has been initialized:*
```
# 1. Manually slice the ref tensor to 2000 (form is spectrogram already)
ref_spec = ref_spec[:, :2000]

# 2. Build the 4D input
ref_spec = ref_spec.unsqueeze(0).unsqueeze(0)

# 3. Run the model live
_, ref_output, _ = param_estimator_model(ref_spec)
print(ref_output[0, 0, :3].tolist())
[0.4803466796875, 0.5720597505569458, 0.8722519874572754]
```

Result *matches* 0.4660 reference. So what the model works, the weights are loaded correctly, for both encoder and estimator. What is wrong with spectrogram preprocessing?

**FILL IN DEBUGGING: WHY STANDARDIZE SPECTROGRAM INPUT?**

Data standardization for the spectrogram input is defined in the MelSpectrogram class but never called.

```Python
def stdze(in_array: np.ndarray) -> np.ndarray:
    # standardize data
    return (in_array - np.mean(in_array)) / np.std(in_array)
```

When updating Philipp on the missing standardization he informed me that this is a step required for the convolutional neural network and that it actually is unusual to be used on spectrograms.

I created the script [`visualize_spectrograms.py`](../visualize_spectrograms.py) to get:

![spectrogram_comparison.png](../spectrogram_comparison.png)

The comparison shows the model was not trained on raw Decibels but on Standardized Spectrograms. By calculating the mean and standard deviation of the spectrogram and transforming it to `(x - mean) / std`, we achieved alignment with the research environment.

- Committing inference debugging branch to repo

  - how to manage BAPE repo within my project?
    - Submoduling
      - Pros: easily pull BAPE updates
      - Cons: difficult to manage, adds complexity to your Docker builds.
    - Vendorring
      - Pros: stability, project is "self-contained." The Docker build doesn't need to reach out to BAPE GitHub. 
      - Cons: manually copy files in case of BAPE updates