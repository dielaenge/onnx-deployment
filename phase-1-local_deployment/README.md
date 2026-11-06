# Phase 1 — Local Deployment
*Building a dummy model and wrapping it in a local inference service.*

The project starting point: an ONNX Runtime inference service running localhost, exposed via a command-line interface and a FastAPI HTTP endpoint. 
This phase establishes the serving scaffold (audio in > acoustic parameters out) against a dzmmy model, before the actual BAPE PyTorch model was available and exported to ONNX in [Phase 3](../phase-3-proper-infra).

**Stack:** 
- CLI
- Python 
- ONNX Runtime 
- FastAPI

**ONNX-Model**: [`dummy_acoustic_model.onnx`](dummy_acoustic_model.onnx) produces placeholder results with no acoustic meaning. 
This phase is an exercise in scaffolding and prepares for production-grade deployments using the actual BAPE model.

→ Next: [Phase 2](../phase-2-manual_cloud_deployment) takes this service to a first naive cloud deployment.
