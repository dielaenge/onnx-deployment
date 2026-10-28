# Phase 7 — Distributed Hot-Path / Cold-Path Inference

> Real-time streaming inference decoupled from asynchronous post-processing initiated via queue.

Phase 7 splits the single real-time service from [Phase 6](../phase-6-production-ready) into two independently-scaled workloads on **ECS Fargate**:

- a **hot path** — *"get live results"*; latency-sensitive, real-time inference streamed over WebSockets, and
- a **cold path** — *"review the entire session"*; latency-insensitive, full-recording processing driven asynchronously through SQS.

The design goal: 
Establishing a real-time inference service was a valuable increment but, in the interest of research users, both live results and analysis of (past) recording sessions must be made available.
This is foundational to separating pipelines: post-processing a full recording must never introduce latency to or drop a live connection. 

Thus, live-inference and post-processing run on two separate paths as separate Fargate services from the same image. They communicate via S3 event notifications which occur when a recording ends, presigned URLS are generated and land in the SQS queue from where the worker process takes over.

## Architecture

```mermaid
flowchart TB
    subgraph Browser
        MIC[Mic → `RealTimeAudioProcessor`<br/>`src/processor.js`]
        VIZ[D3 charts + spectrogram canvas]
    end

    CF[CloudFront<br/>static HTML/CSS/JS frontend from S3 / OAC]

    subgraph HOT["Hot path — bape_ecs_service (Fargate, behind ALB)"]
        WS["WS /ws — FastAPI"]
        SPEC[MelSpectrogram once per chunk]
        T60[(T60 ONNX)]
        C50[(C50 ONNX)]
    end

    subgraph COLD["Cold path — worker_ecs_service (Fargate, no LB)"]
        WK[worker.py — long-polls SQS]
        FF[FFmpeg normalize + full-res MelSpectrogram]
    end

    Q[[SQS bape-cold-path-queue]]
    S3[(S3 bape_app_data_phase7<br/>uploads/ · processed/ · spectrograms/)]

    MIC -- 200ms Float32 chunks --> WS
    WS --> SPEC --> T60 & C50
    T60 & C50 -- JSON params/quantiles + spectrogram --> VIZ
    CF -. serves .-> Browser

    MIC -- on stop: WAV --> S3
    S3 -- ObjectCreated uploads/ --> Q
    Q --> WK --> FF --> S3
    S3 -. presigned GET poll .-> VIZ
```

## Hot path

Browser mic audio is 
- captured by `RealTimeAudioProcessor`, an extension of ([`AudioWorkletProcessor`](https://github.com/dielaenge/onnx-deployment/blob/106f0a5ab71e4ff428a1a68442eb474918217c61/phase-7/src/processor.js#L2)), 
- buffered into 200 ms / 3200-sample chunks, and 
- streamed as raw binary `Float32Array` over the WebSocket. 

The server ([`app/main.py`](app/main.py) `WS /ws`) 
- keeps a rolling **4 s (64000-sample) [`audio_buffer` and runs an inference loop](https://github.com/dielaenge/onnx-deployment/blob/106f0a5ab71e4ff428a1a68442eb474918217c61/phase-7/app/main.py#L123-L167)**, 
  - deletes the oldest 200ms/3200 sample-chunks and adds new, incoming chunks,
- processes a new 4 second spectrogram every 200ms (), and 
- [runs both ONNX models **concurrently**](https://github.com/dielaenge/onnx-deployment/blob/106f0a5ab71e4ff428a1a68442eb474918217c61/phase-7/app/main.py#L169-L176) 
- streams back response_json (params / quantiles / latents for both models, the newest spectrogram `spectrogram_latest100frames`, and `inference_time_ms`). Measured inference is ~30–60 ms per stride after warmup.

## Cold path

On mic stop, the browser encodes the full recording to WAV client-side, fetches presigned URLs from `GET /api/presigned-urls`, and `PUT`s the WAV directly to S3 (`uploads/` prefix) — bypassing the API server entirely. An S3 `ObjectCreated` notification (filtered to `uploads/` to avoid a processing loop) enqueues to SQS. The worker ([`app/worker.py`](app/worker.py)) long-polls the queue, downloads the WAV, normalizes it with FFmpeg, regenerates a full-resolution spectrogram, uploads results to `processed/` / `spectrograms/`, and only then deletes the SQS message. The browser polls the presigned download URL (exponential backoff) until the results are ready.

## Key engineering decisions

- **Separate ONNX models for T60 and C50**, run concurrently; each estimator can be re-exported or re-weighted independently via [`conf/exporter.yaml`](https://github.com/dielaenge/onnx-deployment/blob/106f0a5ab71e4ff428a1a68442eb474918217c61/phase-7/conf/exporter.yaml).
- **Training / inference dependency split** — the phase 7 image ships `onnxruntime` + `fastapi` (~150 MB), while dependency groups required for the ONNX export are opt-in via the `uv` flag `--group onnx_export`; `uv sync` does not install the export packages and the Dockerfile does not require them.
- **Split Terraform state** — To speed up deployment without increasing costs the terraform code base was split into two separate layers:
  - [`terraform/persistent/`](terraform/persistent) (S3, ECR, SQS, IAM, CI/CD OIDC) and 
  - [`terraform/compute/`](terraform/compute) (VPC, ECS, ALB, CloudFront)
  
`/compute`, the cost-driving layer, can be destroyed and re-applied without touching `/persistent` state.
- **No NAT Gateway** — private subnets reach AWS services through VPC interface/gateway endpoints (S3, ECR, CloudWatch Logs, SQS), whcih avoids NAT costs but introduces endpoint costs.
- **Privacy by design** — voice recordings and spatial information of users are sensitive data, which the project does not want to manage. Therefor all data written to S3 has a 1-day lifecycle expiry and is only ever processed in RAM writing nothing to storage; this is a deliberate decision for minimum data retention.
- **Numerical-parity CI discipline** — the [ONNX exporter self-tests](https://github.com/dielaenge/onnx-deployment/blob/106f0a5ab71e4ff428a1a68442eb474918217c61/phase-7/scripts/param_estimator-onnx_exporter.py#L146-L182) against [reference PyTorch outputs (`cfg_output_tuple`)](https://github.com/dielaenge/onnx-deployment/blob/106f0a5ab71e4ff428a1a68442eb474918217c61/phase-7/scripts/param_estimator-onnx_exporter.py#L126-L135) before export.

## Known open issue

The hot and cold paths compute spectrograms via genuinely different code paths (`processor.js` + numpy vs. FFmpeg + `MelSpectrogram`), which introduces measurable numeric drift. Refactoring the worker to replicate the hot path's 4-second sliding local standardization reduced feature drift from an MSE of ~1.5 to **~0.015**. [`scripts/compare_pipelines.py`](scripts/compare_pipelines.py) and the `spec_hot_*` / `spec_cold_*` dumps exist to keep quantifying it.

---

## Run locally

***Requirements:*** 
* [uv](https://docs.astral.sh/uv/) for virtual environment and installing dependencies.
* [`direnv`](https://direnv.net) to automatically load environment variables (not required when running locally).

1. **Create .venv and launch the main container**
```bash
cd phase-7
uv sync                     # runtime dependencies only, see pyproject.toml
uv run python -m app.main   
```
The run command resolves `UVICORN_HOST/UVICORN_PORT` env variables from the [ECS task](https://github.com/dielaenge/onnx-deployment/blob/106f0a5ab71e4ff428a1a68442eb474918217c61/phase-7/terraform/compute/ecs.tf#L43-L50), or, if run locally, defaults them to `127.0.0.1:8000`

Run locally, the frontend must be served from a local `src/` directory.
In production, running in the cloud, CloudFront serves the frontend from S3.

2. **Connect cold-path pipeline**
The cold-path worker runs as a separate process on ECS and requires AWS credentials as well as the adjacent SQS queue and S3 app data bucket
To use your AWS credentials, copy this to `.envrc` and fill it in: 

```phase-7/.envrc
export AWS_PROFILE=<your-aws-profile>
export ACCOUNT_ID=<your-account-id>
export AWS_REGION=eu-central-1

# in `phase-7/terraform/persistent`, run `terraform apply` 
# produces outputs for SQS_QUEUE_URL and APP_DATA_BUCKET_NAME
export SQS_QUEUE_URL=https://sqs.<region>.amazonaws.com/<account-id>/<queue-name>
export APP_DATA_BUCKET_NAME=<your-bucket-name>

# ONLY required if you want to run the ONNX export from `scripts/param_estimator-onnx_exporter.py` 
# see scripts/README.md
path_add PYTHONPATH "$PWD/bape"
```

3. Start the cold-path worker.
```bash
uv run python -m app.worker
```

### Exporting the ONNX model
The model export pipeline is **not** part of `uv sync`, but can also be reproduced, see [`scripts/README.md`](scripts/README.md).


## Layout

```
phase-7/
├── app/            FastAPI hot path (main.py), cold-path worker (worker.py), inference_engine.py
├── src/            Frontend — index.html, app.js, processor.js (AudioWorklet)
├── scripts/        ONNX exporter, compare_pipelines.py — see scripts/README.md
├── conf/           Hydra config for the exporter
├── terraform/      persistent/ + compute/ (two independent root modules)
├── Dockerfile      Single image; hot and cold services differ only by task command
└── pyproject.toml  Dependencies and dependency groups; uv.lock pins exact versions
```


