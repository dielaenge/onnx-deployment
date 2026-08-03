# Phase 3 — Decision Log: Production Networking & Model Onboarding

In Phase 3 the foundation was built and a serious cloud deployment was next. 
Two obstacles were cleared for this to happen: 
1. I was permitted access to the **real BAPE research model and trainig repository**
2. I rebuilt the naive single-EC2 arch from Phase 2 as an **securely isolated, load-balanced VPC architecture** — deployed by hand via the AWS CLI – deliberately, before adopting Infrastructure-as-Code in later phases.

This log records the decisions and their trade-offs. 
Diagrams live in the phase's `README.md`. This phase took *a lot* of manual resource creation leading to lengthy notes including exact resource IDs, which are intentionally omitted here.

---

## Part A — Productionizing the real model

### Decision 1 · Reverse-engineer the model instead or importing the training repo / ONNX or PyTorch model

**Context.** I was given access to the BAPE research repository and a `.pth` weights file. The repo is a
large, unfamiliar PyTorch training codebase driven by Hydra configs. It was built for training and
experimentation, not deployment.

**Decision.** To understand the training repo, I tried to retrace how it instantiates the model harness allowing me to reverse-engineer the model from its Hydra`.yaml` configs. For this I wrote a self-contained `exporter.py` that reconstructs the architecture, loads the pretrained weights, and exports a single portable `speech_encoder.onnx` artifact.

**Rationale.** A deployed ML model inference app should not carry a research training stack as a dependency. A
static-analysis pass over the configs revealed the exact input contract — a 4D tensor Mel
spectrogram (`n_mels=16`, `trunc=2000`). Exporting the ONNX file decouples the deployment entirely from the upstream repo.

**Consequences.** A clean, versioned model artifact I could store in S3 and pull at runtime. The
cost was a genuine "code archaeology" effort (tracing configs, matching tensor shapes, key-renaming
the state dict) — documented separately as its own investigation `MLOps_code-archealogy.md` (TBD).

### Decision 2 · How to feed the model and how to convey the results (TBD: Is this really a decision!?)

**Context.** The model only produces correct results if the audio is transformed identically to how
it was during training (4 seconds, 16kHz mono, WAV), and it emits multiple output tensors rather than a single vector.

**Decision.** I rewrote `audio_processor.py` to reproduce the BAPE MelSpectrogram pipeline before model input exactly,
including a 2D → 4D tensor expansion (`[Height, Width] → [N, Channels, Height, Width]`), and augmented the JSON response into a
more self-documenting object stating inference metadata, primary parameters (T60) and secondary attention weights(TBD: latents!?).

**Rationale.** The deployment is only valuable as long as it does not introduce any drift, so (preprocessing) parity is non-negotiable for inference correctness. A richer, labelled response is also more useful to any downstream consumer than a bare array.

**Consequences.** Correct end-to-end inference locally against the FastAPI wrapper, and an API
contract that carries meaning rather than raw numbers.

---

## Part B — Cloud architecture

### Decsion 3 · Custom VPC with `/24` subnets over a `10.16.0.0/16` range

**Context.** Phase 2's instance sat on AWS' default networking. A production-grade deployment deserves a designed, isolated
network and as the developer I wanted to experience the workings of a custom-VPC first-hand.

**Decision.** A custom VPC at `10.16.0.0/16`, subnetted into `/24` ranges (256 addresses each)
rather than the initially-sketched `/17` split.

**Rationale.** `10.16.0.0/16` deliberately avoids the commonly-used low `10.x` ranges, like `10.1.`, `10.2`., …, to reduce the
chance of future peering/VPN collisions. The first `/17` proposal gave each subnet ~32k addresses —
half the VPC — leaving no room to grow. `/24` ranges keep the plan extensible, with 256 possible subnets, each with 256 possible IP addresses.

**Consequences.** A clean, room-to-grow VPC plan, which avoids VPC collisions and that carried forward as the template for later
phases.

### Decsion 4 · How to keep the EC2 instance private and safe and still deliver results

**Context.** In Phase 2 the application server was directly internet-facing and thus publicly available (TBD: is this true?).

**Decision.** I put the EC2 instance into its own **private** subnet with no public IP. Ingress traffic arrives
only through an **Application Load Balancer** in the public subnets. Outbound access (serving results, package
updates, pulling the model) goes through a **NAT Gateway**.

**Rationale.** Compute resources should never be directly reachable from the internet. An ALB in
front gives a single controlled ingress point and health-checked routing, while a NAT Gateway lets the
private instance reach out without being reachable inbound.

**Consequences.** A conventional public-frontend / private-compute topology — and the first appearance
of the NAT Gateway which became a main cost driver I needed to engineer away.

### Decision 5 · Accept a two-AZ ALB with a single instance — a deliberate learning compromise

**Context.** For development purposes, I wanted a minimal resource footprint, and tried to proceed with a single public subnet but an ALB requires **at least two Availability Zones** enabled. That forced me to create a second public subnet and a second ALB node even though I was still planning to deploy only one backend target — a setup that "doesn't make sense", because the reason for load balancing is to distribute load on multiple backends.

**Decision.** Comply with the ALB's two-AZ requirement: a fully subnetted two-AZ VPC — **two public subnets** (ALB nodes, NAT Gateway) and **two private subnets** — but run only **one** EC2 instance, leaving the load balancer with a single healthy target. Again, not realistic when load-balancing.

**Rationale.** A highly-available load-balancer layer in front of a single point of failure is architecturally lopsided. But the requirement to save costs was real, and building it was the fastest way to *experience* the constraint firsthand. Adding a second instance for true HA was avoidable cost at this stage.

**Consequences.** A knowingly-imbalanced but instructive topology, and a clear-eyed understanding of why real HA means redundant *targets*, not just redundant load-balancer nodes. Flagged explicitly as a dev-only compromise.

It also produced a concrete gotcha worth recording: **an ALB only routes to targets in the Availability Zones it has enabled.** The instance had to be launched into a private subnet whose AZ the load balancer actually covered — placing compute in "a private subnet" was not sufficient, it had to be *the right one*. It's obvious in hindsight but was invisible until traffic failed to reach a healthy-looking instance.

### Decision 6 · Zero-trust access: SSM instead of SSH, TLS terminated at the ALB

**Context.** The Phase 2 box was administered over SSH with an open port 22.

**Decision.** No SSH ports open at all — instance administration via **AWS Systems Manager (SSM)**
only. TLS is terminated at the ALB.

**Rationale.** An open SSH port is a attack surface. SSM gives auditable, key-less access
without exposing a port, and terminating TLS at the load balancer centralizes certificate handling.

**Consequences.** A materially smaller attack surface and a cleaner security story than Phase 2. Traffic on AWS infra is not TLS-secured starting at the ALB.

### Decision 7 · The microphone / HTTPS secure-context wall

**Context.** The main point of the BAPE app is to process microphone input, and modern browsers only grant
`getUserMedia` in a **secure context**, meaning valid HTTPS which requires a valid TLS/SSL certificate. So I generated a self-signed cert and imported it to AWS Certificates Manager (ACM).

**Decision.** I deployed the ALB with an HTTPS listener with the self-signed cert. Without a CLoudFront distribution in place, I had to accept that **browser microphone access requires a certificate from a trusted Root Certificate Authority (CA) — which requires owning a domain name** I didn't have at that point. Microphone capture was replaced by a temporary **file-upload fallback** instead.

**Rationale.** A self-signed cert satisfies TLS termination but not the browser's trust check for mic access. Buying a domain and provisioning a public cert was not in the scope for this phase. The file-upload path proves the inference pipeline end-to-end regardless.

**Consequences.** A concrete, documented limitation and a clear prerequisite (real domain + trusted cert or CloudFront distribution) carried into later phases and made a CloudFront Distribution which handles the certification necessary.

### Decision 8 · Deploying via the AWS CLI or as IaC

**Context.** Everything built via a cloud provider could have been written in Terraform from the start.

**Decision.** For the first phases I decided to build the entire stack by hand with the AWS CLI, documenting every resource and its returned IDs iteratively as they were created.

**Rationale.** I wanted to understand each resource and its dependencies concretely — subnet before
route table, EIP before NAT Gateway, instance before target registration — before hiding the complexity
behind an abstraction. The manual work and the complexity of managing manually deployed resources was overwhelming and made me experience the benefit of Terraform and IaC first-hand.

**Consequences.** I developed a deeper familiarity with the inner workings of my infra and felt the pain: to save on costs I tore down cost-generating resources (NAT Gateway, ALB, EC2) were **at the end of every session and
rebuilt on return**. Keeping momentum when rebuilding was only possible through meticulous documentation of all commands and resulting attributes. That friction made the move to Infrastructure-as-Code in the following phases a no-brainer.

---

## Outcomes

- **Validated infrastructure:** 
  - custom VPC (`10.16.0.0/16`) spanning two AZs with 2 public and
  2 private `/24` subnets, 
  - two ALB nodes, a NAT Gateway, and a single `t3.small` (20 GB gp3) EC2 instance
  loading the model from S3 at boot via `user-data` shell script
  - static fronted built on Tailwind CSS
- **Security:** no open SSH, SSM-only administration, TLS terminated at the ALB; unsecured traffic on AWS premises
- **Known limitation:** live microphone capture blocked by requirement of a trusted cert; circumvented via file upload and CDN
- **Cost reality:** This small setup was already costing ~\$2.50/day, dominated by **idle** NAT Gateway and ALB charges.

That last point sets up Phase 4: the running costs here are almost entirely idle infrastructure, so
the next move is to **eliminate the NAT Gateway and the always-on compute** by refactoring to a
serverless model.