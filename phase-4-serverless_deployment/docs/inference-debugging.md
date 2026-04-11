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

### Implementng bug fix to phase 5

- commit all debug/inference-sandbox file edits
- copy fixed `bape_v2_standardized.onnx` and `bape_v2_standardized.onnx.data` to phase 5 folder
- copy `param_estimator-onnx_exporter.py` to phase 5 folder

- update phase 5 folder structure to
```
  root/
  - app/
    - audio_utils.py (was audio_processor.py)
    - inference_engine.py (was model_processor.py)
    - main.py
    - __init__.py
  - models/
    - `bape_v2_standardized.onnx`
    - `bape_v2_standardized.onnx.data`
  - scripts/
    - param_estimator-onnx_exporter.py
  - terraform/
    -  (…).tf
  - Dockerfile
  - requirements.in
  - requirements.txt
```

===============================
--- Switch to Intel MacBook ---
===============================

- from `pathlib import Path` for `main.py`
  - implement path logic, to identify
    - base directory
    - model path
  - clear `sys.path` workarounds

- add __init__.py to enable app logic in uvicorn command:
`python -m uvicorn app.main:app --reload`

- new structure (app/, scripts/, models/) separates tools (exporter) from engine/API

```
phase-5-container-orchestration/
├── app/                  # Logic needed for the container
│   ├── main.py           # (Your API code)
│   ├── audio_utils.py    # (Your MelSpectrogram & Preprocessing classes)
│   └── models/           # Your standardized .onnx file
├── scripts/              # "Lab tools" not needed in production
│   └── exporter.py       # The script that creates the ONNX
├── terraform/            # Your IaC
└── docs/                 # Your decision logs
```

- fixing venv issues
  - killing old venvs
  - keep new venvs out of sync (icloud & github)
  - create new venv on Intel MB
  - configure `direnv`
    - add `layout python python3.11` to `.envrc` to automatically load `python3.11` virtual env
  - install requirements

- bug fixing
  - updated onnx model export (`dynamo=True`) is based on newest [IR version](https://www.google.com/url?sa=E&q=https%3A%2F%2Fonnx.ai%2Fonnx%2Fintro%2Fconcepts.html%23ir-versions) and requires a onnxruntime version >1.17.0, which was fixed in the requirements.in at 1.16.3 because of old export configs
  - standardization syntax error in `audio_utils.py`: did not subtract mean from `full_spectrogram_2d` before division
  - first test run failed to resolve "dot" notation for import (`from .audio_utils import …`)
    - created empty `__init__.py` to recognize `models/` folder as package
    - as main.py now uses relative imports it must be launched as a module
    (`python -m uvicorn …`)

  - shape error: onnx runtime expects numpy array while `preprocess_audio` was returning `batched_spectrograms_4d` as a tensor
    - used Debugger to follow shape at breakpoints and modify to fix


=====================================
--- Switch back to Apple Silicone ---

Snapshots to summarize:

*Overall:*
I took some time to retrace what I did during my visit as I was pretty distracted during that time.
Maybe you can help – in that regard, you must consider that you provided straight forward guidance and I was trying to follow though I would actually like to become more knowledgeable and in command, don't paint it as if I was understanding and memorizing everything entirely and perfectly, rather assume I kept the basics at best, also take into consideration, what information I gave you and questions I asked and defer an objective grade of what I actually did and learned.

> Here is your objective grade:
> - What you actually learned/own: You understand why we are doing this. You grasped the concept of the sliding window, you correctly identified that the reference input needed to be verified, you understood that "shapes" and "types" have to align between PyTorch and ONNX, and you understand the necessity of having "clean" paths.
> - What you do NOT own yet: The exact syntax muscle memory, the advanced Git recovery maneuvers, and the deep mechanics of how Python resolves its environment behind the scenes.
> - The Verdict: This is exactly where a Junior/Mid Cloud Engineer should be. You have the architectural vision, but the syntax still feels like a foreign language. That is normal.


*direnv:*
I think I'm starting to make sense of the direnv install. If it's installed it does something with ~/.zshrc (which I currently can't access from my M4 terminal !?) and then checks for an .envrc file in every folder that is opened in order to then invoke environment variables and virtual environment configs which are then written to a .direnv folder.

> You said: It does something with ~/.zshrc (which I can't access).
> - Clarification: You can access it! ~ just means your home folder (/Users/davidgoossens). The . means it's hidden. If you type cat ~/.zshrc in your terminal, you will see the eval "$(direnv hook zsh)" line. This line simply tells your terminal: "Every time David changes directories, run direnv."
>You said: It checks for an .envrc file in every folder... invokes environment variables and venv configs...
> - Correct.
>You said: ...which are then written to a .direnv folder.
> - Essential Correction: It doesn't write configs to .direnv. When you put layout python python3.11 in your .envrc, direnv literally runs python3.11 -m venv .direnv/python-3.11. That folder IS your virtual environment. It's just a standard venv that direnv manages automatically so you don't have to type source activate.
> You observed: Separation of separate direnvs for phase 4 and phase 5.
> - Correct & Essential: Because you have an .envrc in Phase 4 and a different one in Phase 5, direnv creates two entirely separate Python universes. Phase 4 cannot accidentally use a library installed in Phase 5. This is the definition of "Environment Parity."

*Syncing*
Using iCloud and git/GitHub across two different CPU architectures (Apple Silicone M4 / Intel ARM64) became weird and needed clarification.

> ### Rule 1: Git is for Code. iCloud is for Artifacts.
> Git is the Source of Truth. If the MacBook dies, whatever is on github.com is what survives. However, Git hates large binary files (like the 15MB .onnx models). Use iCloud to automatically sync larger files between Macs.

> ### Rule 2: Environments (`.direnv`, `venv`) MUST NEVER SYNC.
> Python environments contain binary files compiled specifically for the CPU that built them.
>> The Practical Step: Ensure `.direnv/` and `venv/` are in your `.gitignore`. Also, if possible, you don't want iCloud syncing them because it wastes bandwidth. (This is why we used `.nosync` earlier, but since we are using `direnv` now, we just have to accept iCloud might sync .direnv. 
>> WHEN SWITICHING MACS:
>>```
>>rm -rf .direnv && direnv allow
>>```
>>  to rebuild locally

### Rule 3: The "Lid Open / Lid Close" Protocol.
> Closing the laptop: 
> ```
> git add .
> git commit -m "wip"
> git push
> ```
> Opening the Mac Mini: 
> ```
> git fetch
> git status
> git pull
>```

=====================================

- git stashing changes made on M4 before pushing on IntelMB
- on IntelMB: `git push origin feat/container-orchestration` to push changes
  - among others: .numpy() on final 4D batched spectrogram enabled switch from PyTorch tensor math to ONNX's C++ runtime (array-based)
- on M4: `git pop` to add stashed changes

- removed .direnv and allowed direnv
- install torch, torchaudio, pip-tools
- compile requirements.in
- install requirements

- run updated `main.py` locally and test with reference file wet_speech.wav
  - result parity with reference results

## Building back the frontend

- at the start of debugging, I reverted to the last *one-shot* version, meaning the app produces one estimation result regardless of the input löength, instead of slicing it to overlapping 4 second chunks and producing an estimation result for each chunk

- I want to build back to the full system before picking up where I left off for debugging

- add slicing logic to audio_utils.py, which currently produces one set of estimates for inputs of any length
  rubber duck version:
  - define a size for slices (window)
  - define overlap / stride (having overlap allows denser, smoother results)
  - define empty list for slices
  - define empty list for timestamps

  - loop through full input tensor, 
    - slicing it to defined size with defined step size
    - when the last slice is smaller than the defined size
      - make it a numpy array and pad it to the right, with whats missing
    
    - in each step, calculate timestamp_sec by dividing current first frame number of slice by 500, as 500 frames are 1 second
    - append timestamp_sec to the timestamps_sec list

  - before, the one-shot spectrogram came out as a pytorch tensor and I used unsqueeze() to add required dimensions
  - now, the slices added to the list are numpy arrays already, so I use np.expand_dims() to augment it to it's final preprocessed batched_spectrograms_4d shape

- after implementing the changes, a first local test resulted in 

```zsh
onnxruntime.capi.onnxruntime_pybind11_state.RuntimeException: [ONNXRuntimeError] : 6 : RUNTIME_EXCEPTION : Non-zero status code returned while running Reshape node. Name:'node_view_1' Status Message: /Users/cloudtest/vss/_work/1/s/onnxruntime/core/providers/cpu/tensor/reshape_helper.h:47 onnxruntime::ReshapeHelper::ReshapeHelper(const TensorShape &, TensorShapeVector &, bool) input_shape_size == size was false. The input tensor cannot be reshaped to the requested shape. Input shape:{125,2,768}, requested shape:{125,1,3,256}
```

- when I exported the current onnx model, the export was successful but I also received `UserWarning: 'dynamic_axes' is not recommended when dynamo=True...`.

- In my exporter script this is still the case and as it is till broken for phase 5 because of missing pathlib logic, we need to fix this next


