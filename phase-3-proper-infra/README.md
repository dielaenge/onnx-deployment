# Phase 3 — Proper Infrastructure
*A manual VPC design and the integration of the real model.*

> Pending:
> - Architecture diagram 

Introduces a production-shaped network: a custom VPC with public and private subnets across two availability zones, behind an Application Load Balancer, served over HTTPS. This phase also did the "code archaeology" — reverse-engineering the real Fraunhofer **BAPE** PyTorch model from the research codebase and exporting it to ONNX with a numerical-parity check, replacing the stand-in model used in Phases 1–2.

**Stack:** AWS VPC (public/private subnets, 2 AZs) · ALB · EC2 · HTTPS/TLS · PyTorch → ONNX export

→ Next: [Phase 4](../phase-4-serverless_deployment) explores a serverless alternative.
