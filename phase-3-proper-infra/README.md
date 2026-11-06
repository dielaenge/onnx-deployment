# Phase 3 — Proper Infrastructure
*A manual VPC design and the integration of the real model.*

> Pending:
> - Architecture diagram 

Introduces a production-shaped network: a custom VPC with public and private subnets across two availability zones, behind an Application Load Balancer, served over HTTPS. This phase also did the "code archaeology" — reverse-engineering the real Fraunhofer **BAPE** PyTorch model from the research codebase and exporting it to ONNX with a numerical-parity check, replacing the stand-in model used in Phases 1–2.

**Stack:** 
- AWS VPC (public/private subnets, 2 AZs)
- ALB
- EC2
- HTTPS/TLS
- PyTorch → ONNX export

**Model**: First ONNX export using the BAPE model architecture and weights. First exported as `onnx/speech_encoder.onnx`, then additionally as `onnx/super_param_estimator.onnx` to export `latent_vector`, the acoustic fingerprint. Estimated params produces T60 estimates. 
This phase’s export is a snapshot / result of my code archaeology and the attempt to retrace the original BAPE repo. 
The T60 results at this stage have not yet been validated.

→ Next: [Phase 4](../phase-4-serverless_deployment) explores a serverless Function as a Service alternative.
