# Phase 6 — Production-Ready Real-Time

> From request/response to a live stream.

Replaces REST request/response with a stateful, low-latency **WebSocket** connection: raw microphone floats stream from the browser's Web Audio API straight into the model, and live inference results are visualised with **D3.js**. Deployed behind an ALB and CloudFront CDN, with structured JSON logging for MLOps observability.

**Stack:** WebSockets · Web Audio API · D3.js · ECS Fargate · ALB · CloudFront

→ Next: [Phase 7](../phase-7) splits this into decoupled hot and cold paths.
