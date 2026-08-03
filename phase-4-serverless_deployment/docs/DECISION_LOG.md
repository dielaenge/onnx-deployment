# Phase 4 — Decision Log: Serverless Refactor & Scale-to-Zero

Phase 3 ended with a validated but rather expensive architecture: roughly **\$2.50/day, almost entirely idle cost** from an always-on NAT Gateway, ALB and EC2 instance. 
Phase 4 is the consequence: rebuild the same inference service so that **it costs nothing when nobody is using it**, while experiencing the downside of cold-starts.

Another task for phase 4 was **separation of concerns**: the frontend leaves the application server for good, and large binary results stop travelling inside JSON responses.

---

## Decision 1 · Refactor to Lambda to eliminate idle cost

**Context.** Phase 3's running cost was caused by infrastructure sitting idle, because NAT Gateways and an ALBs are billed by the hour whether used or not.

**Decision.** Move the inference workload to **AWS Lambda** — pay per invocation and per millisecond of execution, nothing while idle.

**Rationale.** For a portfolio service with sporadic, bursty traffic, always-on compute is the wrong shape entirely. Lambda inverts the cost model. It also removes the NAT Gateway outright: Lambda runs outside my VPC on AWS infra by default and reaches public AWS services (S3) directly, so there is no private-subnet egress to pay for.

**Consequences.** Idle cost approaches zero. In exchange I inherited **cold starts**, which were significant as my image was ~900 MB image plus an ~13 MB ONNX model. On a cold invocation this became the central performance concern of this phase.

## Decision 2 · Package as a container image, from ECR, not a ZIP

**Context.** With roughly 900 MB, my set of dependencies (ONNX Runtime, librosa/numpy/scipy, FFmpeg, matplotlib) was far
beyond Lambda's 250 MB unzipped limit for standard deployment packages.

**Decision.** Instead of deploying my app as a ZIP to Lambda, I containerized it as a **container image** built on the AWS-managed Python 3.11 base image and stored in **Amazon ECR**. This allowed for an uncompressed size limit of up to 10 GB.

**Rationale.** Container images raise the limit to 10 GB, which the dependency set requires. I chose ECR
over Docker Hub because it natively authenticates via **IAM roles**, supports **scan-on-push** vulnerability inspection, and integrates with the AWS stack.

**Consequences.** A reproducible build, but a large one — and image size directly feeds the cold start problem. As this was my first real Dockerfile, I also learned about layer-cache ordering: rarely-changed layers, like `requirements.tx` should be copied before frequently-edited ones, like `api.py`, in order to not slow down iteration speed. Docker builds from top to bottom and loads layers from its cache. When a layer has any kind of change it's invalidated and so are all layers beneath. Since my dependencies were quite big, it was key to have them go on top when `COPY`ing in my Dockerfile.

## Decision 3 · Lambda Function URL instead of API Gateway

**Context.** A Lambda function needs a public entry point. My first candidate was API Gateway, but the Lambda documentation surfaced Function URLs first.

**Decision.** Expose the function via a **Lambda Function URL**.

| | Lambda Function URL | API Gateway |
|---|---|---|
| Cost | no additional cost | per-call — potentially the most expensive component |
| Setup | simple | more involved |
| Integrations | IAM | most AWS services |
| Timeout | **15 minutes** | 29 seconds |
| Transport | HTTPS by default | HTTP by default |

**Rationale.** API Gateway is the more advanced tool when you need request transformation, throttling, usage plans or broad service integration, which were all beyond my app's scope. At the same time, the timeout limit for an API Gateway is much less and did not leave a lot of buffer **execution time** (inference on a cold start can be slow) and **no per-request cost**.
API Gateway's 29-second timeout is a hard ceiling that a cold start could realistically breach – the Function URL's 15 minutes removes that risk entirely.

**Consequences.** Cheaper and simpler, with the timeout risk designed out. The downsides are fewer
API-management features, which I accepted for a single-endpoint service in development, and the less management features result in reduced protection and security. That's why I deployed a CF distribution in front, which makes the function URL private. 

## Decision 4 · Bridging the FastAPI vs. Lambda event-model gap

**Context.** FastAPI speaks ASGI/HTTP while Lambda invokes handlers with JSON event payloads. These do not natively fit together, a translation problem I did not know existed before this phase.

**Decision.** I found the [AWS Lambda Web Adapter](https://github.com/aws/aws-lambda-web-adapter) as a way to run the unmodified FastAPI app inside Lambda.

**Rationale.** The alternatives were AWS Powertools, which is actually more light-weigth and built for Lambda-specific performance, or switching web frameworks entirely, but using the Web Adapter allowed me to keep my FastAPI app as is and keep momentum. So szicking to FastAPI meant the application code stayed identical to Phase 3 and the only thing changing in this phase was the *deployment model* to Lambda — which was the whole point of the exercise.

**Consequences.** The application stays unchanged but runs serverless on Lambda instead of self-managed infra, which is exactly what makes the phases comparable.

## Decision 5 (rather a fix) · Re-export the model at a lower ONNX operator set version

**Context.** The Docker container built successfully but the model failed to load at runtime:

> `ONNX Runtime only guarantees support for models stamped with official released onnx opset versions … Current official support for domain ai.onnx is till opset 19.`

I did not pin the the ONNX export to a specific version of operator set (how the model functions internally); the available `onnxruntime` builds supported at most 19.

**Decision.** Re-export the model at an explicitly-pinned, supported opset version (18), rebuilding it in the phase-3 folder's virtualenv, then point the app at the new artifact.

**Rationale.** The original export set no opset version, so it defaulted to the newest (opset 20), which was not supported by the `onnxruntime` version supported on the Lambda / Python 3.11 image (only ≤1.16.3 was installable), so the artifact was the only side of the contract I controlled. Because each phase folder keeps its own virtualenv, Phase 4's had already been stripped of the export toolchain, so I re-ran the export from the phase-3 folder's environment (a directory + venv switch in the same working tree, not a branch change).

**Consequences.** A working container, and a sharp lesson: **don't let ONNX export default to the newest opset, but pin it to what the deployed runtime supports**. The model artifact and its runtime are a **versioned contract**.

## Decision 6 · Sizing Lambda resources by measuring, not guessing

**Context.** At the first run, Lambda failed outright because the default memory is 128MB, whereas the app plus dependencies were ~900 MB on disk. Since memory allocation also determines CPU share, it directly drives cold-start duration or even start up failure.
My hot-fix was to just pick 4 GB first before measuring the actual requirements.

**Decision.** Measure the container stats locally with `docker stats` before choosing, rather than guessing.

**Rationale.** Guessing high wastes money on every invocation; guessing low breaks the function.
Measurement was cheap: run the image, watch actual consumption.

**Consequences.** Observed ~600 MB resident and 100 % CPU for a few seconds at startup, dropping to
~35 % during inference on a small `mp3` file. This gave me an evidence-based memory setting instead of a
guessed one. Measuring before sizing also carried into ECS right-sizing later.

## Decision 7 · Private S3 + CloudFront (OAC), not a public website bucket

**Context.** Serving the frontend via S3 static website hosting requires the bucket to be **public**, which was not acceptable from a privacy and security standpoint.

**Decision.** Set the bucket **private** and serve it through a **CloudFront distribution** using
an **Origin Access Control** entity, with a bucket policy granting `s3:GetObject` to that OAC only.
CloudFront also fronts the Lambda Function URL, with CORS scoped to the CloudFront origin and handles the HTTPS encryption.

**Rationale.** Origin Access Control permits exactly one trusted reader of the frontend — the distribution — and keeps the bucket closed to everything else. Routing the API through the same distribution also gives a single origin to the browser, which removes the cross-origin problem instead of loosening CORS.

**Consequences.** A private-by-default frontend and a pattern (CloudFront in front of both static
assets and the API), which carried over into later phases. Configuring the OAC required passing a
JSON config file to the CLI rather than simple flags — my **first step toward Infrastructure as
Code**, and a hint of why Phase 5 adopts Terraform.

## Decision 8 · Claim-check pattern: stop shipping binaries inside JSON

**Context.** Besides showing the inference results, to display the normalized WAV and the rendered spetcrogram to the user, I originally designed the API to return both **Base64-encoded inside the JSON response**. I learned that this increased my payload by ~33 % (stats TBD) and burns Lambda memory, forcing the system to reach its limits. So I needed a way to out source the data storage in this step, away from using the Lambda memory.

**Decision.** Adopt the **claim-check pattern**: upload both WAV file and spectrogram data to S3 under a `results/` prefix and return **time-limited presigned URLs** instead of the data itself. The browser fetches
the artifacts directly from S3.

**Rationale.** The API should return a light-weight *reference* to a larger file or artifact, not the file itself. Uploading the resulting artifacts to pre-signed URLs from where the frontend can pull them, takes load off Lambda memory, keeps responses small, and facilitates the transfer without requiring additional compute.

**Consequences.** This fix allowed for smaller, faster responses and a leaner function. It required granting the Lambda role both `s3:PutObject` (to store) and `s3:GetObject`. Paired with an S3 **lifecycle policy expiring `results/` objects after one day**, so user-derived artifacts are not retained. This is an ongoing privacy-by-design requirement that carries through Phase 7 and is the reason why the application has no database tier yet.

## Decision 9 · Preparing any audio input format with FFmpeg and MelSpectrogram

**Context.** Browsers and phones produce inconsistent audio containers (an iPhone yields M4A, other devices WAV or mp3), and the model preprocessing expects a specific format: a 4 second spectrogram of a 16kHz mono WAV file.

**Decision.** Route **all** uploads through an FFmpeg normalization step producing a consistent
data format before preprocessing further, rather than narrowing the pipeline with specific format requirements.

**Rationale.** Format handling belongs at the edge of the pipeline, once, instead of leaking format
assumptions into the model code. FFmpeg was already a known dependency from Phase 2, but this time
installed cleanly via the Dockerfile rather than configuring it manually directly on the host OS via SSH.

**Consequences.** The service accepts whatever a real user's device produces. In phase 2, installing FFmpeg on a EC2 instance was the major obstacle before proper deployment, in phase 4 containerization turned it into a single build instruction line in the DOckerfile.

---

## Outcome

- **Architecture:** private S3 + CloudFront (OAC) serving the frontend; a containerized FastAPI app
  on Lambda behind a Function URL; ECR for the image; S3 `results/` with presigned URLs and a
  one-day lifecycle expiry.
- **Cost:** idle cost effectively eliminated — the NAT Gateway, ALB and always-on instance are all
  gone.
- **Trade-off accepted:** cold starts, driven mostly by a ~900 MB image and model load time.
- **Carried forward:** the CloudFront-fronts-everything pattern, the claim-check pattern, and the
  retention policy all survive into later phases.

The open question this phase leaves behind is the one Phase 5 picks up: Lambda solved *cost*, but
configuring it involved a growing pile of imperative CLI calls and JSON config files. The next step
is not a different compute model but a different **way of describing infrastructure** —
Infrastructure as Code.
