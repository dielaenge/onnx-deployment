# Phase 4 — Serverless Deployment
*Trade always-on VPC for serverless pay-per-invocation.*

> Pending:
> - Architecture diagram 

Repackages the inference service as a container image on AWS Lambda, exposed through a **Lambda Function URL** (no API Gateway). Moving from an always-on EC2 host to event-driven, pay-per-invocation execution eliminates idle compute cost. 
Excursion: Spectrogram parity check validating that the serverless port matches previous pipeline (phase3) output.

**Stack:** AWS Lambda (Python3.11 container image) · Lambda Function URL · Docker · ECR

→ Next: [Phase 5](../phase-5-container-orchestration) moves to long-running, orchestrated containers.
