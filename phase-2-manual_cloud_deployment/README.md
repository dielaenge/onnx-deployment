# Phase 2 — Manual Cloud Deployment

*First, naive ONNX cloud deployment.*

> Pending:
> - Architecture diagram 

The Phase 1 service launched via *click-ops* on an EC2 instance. 
The manual approach is deliberate: a baseline to feel the operational pain of having no reproducibility nor automation that every later phase works to engineer away.

**Stack:** 
- AWS VPC 
- AWS EC2 
- FastAPI
- FFmpeg, librosa 

**ONNX-Model**: [`dummy_acoustic_model.onnx`](dummy_acoustic_model.onnx) produces placeholder results with no acoustic meaning. 
This phase is an exercise in scaffolding and prepares for production-grade deployments using the actual BAPE model.

**Next:** [Phase 3](../phase-3-proper-infra) replaces a naive, basice deployment with a real network infrastructure.
