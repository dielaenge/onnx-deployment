# Phase 2 — Manual Cloud Deployment

*First, naive ONNX cloud deployment.*

> Pending:
> - Architecture diagram 

The Phase 1 service, stood up manually ("click-ops") on an EC2 instance, with FFmpeg and librosa handling audio decoding and preprocessing. The manual approach is deliberate: a baseline to feel the operational pain — no reproducibility, no automation — that every later phase works to engineer away.

**Stack:** AWS VPC – AWS EC2 – FFmpeg – librosa – FastAPI

**Next:** [Phase 3](../phase-3-proper-infra) replaces click-ops with real, private network infrastructure.
