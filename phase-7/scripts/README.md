# phase-7/scripts
Tooling that is not part of the deployed service. 
Tooling not included in the `:phase7` image, container or in CI workflow.

## `param_estimator-onnx_exporter.py` exports the trained PyTorch model and weights to `.onnx`-files
Exports either BAPE parameter estimator for T60 or C50 params to ONNX, verifies numerical parity against reference PyTorch outputs and writing the file.
onnx stands for [Open Neural Network Exchange](https://onnx.ai/).

***`param_estimator-onnx_exporter.py` script cannot be run from a fresh clone*** as it has three reqs *not included in this repository*:

1. The BAPE research code — `github.com/philipp-goetz/bape`, a private repository.
   Access requires an invitation from its maintainer. Clone it next to this phase and point
   `PYTHONPATH` at it (see [`.envrc.example`](permalink)):
   ```bash
      git clone git@github.com:philipp-goetz/bape.git phase-7/bape
   ```
2. Model weights (`pth`) and reference outputs (`pt`) under `assets/`. not published here.
3. The `onnx_export` dependency group (PyTorch, Hydra, onnxscript):
   ```bash
      uv run --group onnx_export python scripts/param_estimator-onnx_exporter.py
   ```

These are *not required to run, build or deploy the inference service*. 

During CI, the exported `.onnx` files are downloaded from S3 and baked into the image. The latter is subject to change as serving the model from a dedicated service offers room for improving the image build regarding size and efficiency.

### Use Hydra to choose which parameter to export

The script [reads the training run config](https://github.com/dielaenge/onnx-deployment/blob/106f0a5ab71e4ff428a1a68442eb474918217c61/phase-7/scripts/param_estimator-onnx_exporter.py#L38) named in [`conf/exporter.yaml`](https://github.com/dielaenge/onnx-deployment/blob/106f0a5ab71e4ff428a1a68442eb474918217c61/phase-7/conf/exporter.yaml), takes the target parameter from it, and derives the output filename from
that. 

To export C50 instead of T60 either 

- comment/uncomment `run_cfg`, `model_weights` and `output_tuple` in `conf/exprter.yaml` 

or 

- override the three paths on the command line (Hydra), 

   ```bash
   uv run --group onnx_export python scripts/param_estimator-onnx_exporter.py \
   run_cfg=assets/results/param/2025-11-18_19-33-41/config.yaml \
   model_weights=assets/results/param/2025-11-18_19-33-41/model.pth \
   output_tuple=assets/reference_outputs/reference_output_c50.pth
   ```


## `compare_pipelines.py` — hot/cold spectrogram drift

A local debugging tool. 

It 
- loads the `spec_hot_<uuid>.npy` / `spec_cold_<uuid>.npy` dumps from `app/models/`, 
- slides the shorter, hot path, array across the longer one to find the best temporal alignment based on minimum MSE, and reports MSE min and max absolute error at that offset. 

The script expects both hot and cold path specs to be on the same file system under `app/models/`

```bash
# find <fill-in-session-uuid> in `app/models/`
uv run python scripts/compare_pipelines.py <fill-in-session-uuid>
```