# Phase 1 — Local Deployment
*Building a dummy model and wrapping it in a local inference service.*

The starting point: an ONNX Runtime inference service running entirely on the local host, exposed two ways — a command-line interface and a FastAPI HTTP endpoint. This phase establishes the serving scaffold (audio in > acoustic parameters out) against a stand-in model, before the real BAPE PyTorch model was introduced and exported to ONNX in [Phase 3](../phase-3-proper-infra).

**Stack:** Python · ONNX Runtime · FastAPI · CLI

→ Next: [Phase 2](../phase-2-manual_cloud_deployment) takes this service to the cloud.
