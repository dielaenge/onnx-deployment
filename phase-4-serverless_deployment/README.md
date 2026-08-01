# Phase 4 — Serverless Deployment

> Trade always-on compute for pay-per-invocation.

Repackages the inference service as a container image on AWS Lambda, exposed through a **Lambda Function URL** (no API Gateway). Moving from an always-on EC2 host to event-driven, pay-per-invocation execution eliminates idle compute cost — with a spectrogram parity check validating that the serverless port matches the previous pipeline output.

**Stack:** AWS Lambda (container image) · Lambda Function URL · Docker · ECR

→ Next: [Phase 5](../phase-5-container-orchestration) moves to long-running, orchestrated containers.
