# Phase 6 — Inference streaming
*From request/response to a live stream.*

> Pending:
> - Architecture diagram 
> - decision log

Replaces REST request/response with a stateful, low-latency **WebSocket** connection: raw microphone floats stream from the browser's Web Audio API straight into the model; live inference results are visualised. Deployed behind an ALB and CloudFront CDN, with structured JSON logging for MLOps observability.

**Stack:** WebSockets –  · D3.js · ECS Fargate · ALB · CloudFront - Web Audio API

→ Next: [Phase 7](../phase-7) splits this into decoupled hot and cold paths.
