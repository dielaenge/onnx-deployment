# README: Multi-stage ML-Ops

### Intro

- What is this project about?
- What does it do?
- How do I use it?

### **Phase 1: Local deployment with onnx runtime**
- local deployment
- CLI app and FastAPI endpoint

### **Phase 2: Naive Cloud Deployment**
- manually configured, click-Ops EC2 instance
- configured AL2023 server to run FFmpeg as prebuilt app
- updated `audio_processor.py` to use `librosa` instead of `soundfile`

### **Phase 3: Production-Ready Cloud Deployment**
*In this phase, the goal was to transition from the naive manual deployment of Phase 2 to a scalable, secure, and maintainable cloud architecture. This involved designing a custom VPC, isolating services in private subnets, and managing ingress traffic with an Application Load Balancer.*

##### *Detour: Integrating a Real-World ML Model*

At the start of this phase I was invited to the GitHub repo of the real world PyTorch model we are deploying in this project and were substituting with a dummy model until here. 
This required a deep dive into the BAPE repository`s "code archaeology" to reverse-engineer the model's architecture and data preprocessing requirements from a complex, unfamiliar codebase.

**The process involved:**
- **Systematic Code Investigation:** Tracing Hydra `.yaml` configurations to identify the model's structure and dependencies.
- **Environment Debugging:** Resolving a `TimeoutError` by downgrading from an unsupported Python 3.13 environment to a stable 3.11 build.
- **Model Weight Surgery:** Writing a script to parse and rename keys in the pre-trained `.pth` file to match the reconstructed model architecture.
- **Tensor Shape Correction:** Diagnosing and fixing a 4D tensor shape mismatch required by the model's `Conv2d` layers.

The successful result was a self-contained `exporter.py` script that produces a validated `speech_encoder.onnx` model, ready for deployment.

**[➡️ The full, detailed story of the model export process in my Decision Log.](./docs/DECISION_LOG.md#x-embedding-bape)**

## Target Architecture

[ONNX model arch exported with Neutron.app]

Links to all phases (architectures, learnings)
