# Phase 4: Serverless deployment

## 0. Intro and Setup

**Intro: End of phase 3 - requirements for phase 4 and lookout**

Phase 3 was secure and performant but a pain of manual work and much too expensive for the use case (~ 2,50 € / day for EIP, NAT-GW, EC2 instance + EBS, ALB combined).

Phase 4 therefor introduces a serverless deployment with Lambda and will explore if the user experience will be acceptable when cold starting a Lambda instance and if this solution meets basic requirements in terms of costs, performance, security and portability/ease of mainatance.

Why serverless?
What obstacles might occur?

**Setup**
- created and reiterated system instructions with Claude Sonnet4.5 and Gemini3 Pro Preview

- phase 4 setup: 
  - new `phase-4-serverless_deployment` folder
    - copied `src/`, `onnx/`, `static/`, `api.py`, `requirements` and `user_data.sh` (for reference)
  - new `feat/serverless_deployment` branch
  - initialize direnv for phase-4-folder

**General questions**
Is my virtual environment set up properly?
Are my system-wide installs clean?


## 1. Architecture

I switch to AWS Lambda to deploy the model via this serverless function as a service model, instead of managing the server infrastructure myself and paying continuosly for the infrastructure's availability, plus the resources consumed when in use. 
With Lambda I will only pay when the function is called and runs. This usually also means cold-starting the compute resources necessary and will foreseeably become a challenge in this phase.


```Mermaid
---
title: Phase 4 Architecture
---


graph LR
    subgraph User Client
    Browser[User Browser]
    end

    subgraph "BAPE - Frontend"
    S3_Bucket[S3 Bucket - Static Website Hosting ]
    end

    subgraph "BAPE - Backend"
    API_GW[API Gateway]
    Lambda[Lambda Function]
    end

    %% Flow 1: Loading the page
    Browser -- 1. GET index.html (including JS) --> S3_Bucket

    %% Flow 2: Using the app
    Browser -- 2. POST Audio --> API_GW
    API_GW --> Lambda
```

Lambda is usually deployed on AWS infrastructure and has no access to any resources located in a VPC, unless public IPs are provided. Lambda functions have access to public AWS services (like S3) and the public internet. 
To access a Lambda function from the public internet an API Gateway is necessary.



## 2. Docker Setup / Containerization

Q1 **Which Docker image?**

I'm not sure how I should have gotten to this question without this explicit guzidance whivh I don't want to rely on.
BUt then I googled container registries and was reminded that I can mainly source my image (most important for the required runtime) either from Docker Hub or from Amazon ECR.

The Lambda function will need to execute our Python3.11 code, so its OS needs Python3.11.

As I want to move forward efficiently I choose an AWS-managed image with Python3.11 installed and found it at https://gallery.ecr.aws/lambda/python.

I opened the Docker Desktop app and Documentation but am not sure how they'll connect to ECR or if I will get the image from ECR and not from Docker Hub.

I created `Dockerfile`in phase 4 root folder and started sketching out a rough draft, as I have no experience writing Dockerfiles.

Q2 **How to solve the `ffmpeg` dependency?**
In phase 2 the main obstacle was to find a workaround for installing `ffmpeg` which was not available via `dnf`.
I sourced the binary built directly from the source and think this will be a `RUN` command in the `Dockerfile`

Q3 **How to translate HTTP events (FastAPI / ASGI) to Lambda JSON events**
I didn't know about this translation problem before and am worried about getting this hint easily from you…
Ad-hoc I found several approaches to this topic, the most popular: aws-lambda-web-adapter by awslabs on GitHub, then AWS Powertools for AWS Lambda by the AWS Community and I found Hono which is a web framework which is interoperable with AWS Lambda and as a web framework should be an alternative to FastAPI!?
My understanding is too shallow here, so my instinct would be to choose the official solution by the awslabs.

Q4 **How to modify `api.py` to expose function to AWS Lambda**
This, too, is a problem, that would have definitely taken me hours to realize in the first place. So I'm worried about always getting the easy way from you but then also I want to move on and make progress… I don't know what to tell you exactly but you get the problem.

To your question… I am clueless. I guess I also understand too little about how FastAPI works to understand the delta from phase3 to 4


--

Crafting the Dockerfile
- had to understand that RUN commands form the ingredients before the CMD command executes the recipe

- Docker caches each line of the Docker file, so copying frequently edited files to the container before other which are rarely edited forces everything to be loaded again

- dependency problems because requirements.in compiled a list of explicit version dependencies which are based on my local dev environemnt.
  - strip requirements.txt of all explicit versions
  - encounter dependency compatibility issues with numpy>2, scikit-learn and scipy -> had to define explicit legacy versions < v2
  - compatibility issue with onnxruntime (undefined version) and my onnx model:

  ```zsh
    onnx-acoustic/phase-4-serverless_deployment on  feat/serverless-deployment [$!?] via 🐍 v3.13.7 (phase-4-mac-mini) on ☁️  dev (eu-central-1) took 8s 
    docker run --platform linux/amd64 -p 9000:8080 bape-lambda
    
    2026-02-09 22:56:40,465 - API CRITICAL - FATAL: Could not load model at startup. Server will fail on requests. Error: [ONNXRuntimeError] : 1 : FAIL : Load model from onnx/super_param_estimator.onnx failed:/onnxruntime_src/onnxruntime/core/graph/model_load_utils.h:46 void onnxruntime::model_load_utils::ValidateOpsetForDomain(const std::unordered_map<std::basic_string<char>, int>&, const onnxruntime::logging::Logger&, bool, const string&, int) ONNX Runtime only *guarantees* support for models stamped with official released onnx opset versions. Opset 20 is under development and support for this is limited. The operator schemas and or other functionality may change before next ONNX release and in this case ONNX Runtime will not guarantee backward compatibility. Current official support for domain ai.onnx is till opset 19.
    ```
  - set onnxruntime to >=1.19.0 to support the most recent opset version (my model is 20)
    - build command failed again:

    ```zsh
    44.72 ERROR: Ignored the following versions that require a different python version: 0.36.0 Requires-Python >=3.6,<3.10; 0.37.0 Requires-Python >=3.7,<3.10; 0.38.0 Requires-Python >=3.7,<3.11; 0.38.1 Requires-Python >=3.7,<3.11; 0.52.0 Requires-Python >=3.6,<3.9; 0.52.0rc3 Requires-Python >=3.6,<3.9; 0.53.0 Requires-Python >=3.6,<3.10; 0.53.0rc1.post1 Requires-Python >=3.6,<3.10; 0.53.0rc2 Requires-Python >=3.6,<3.10; 0.53.0rc3 Requires-Python >=3.6,<3.10; 0.53.1 Requires-Python >=3.6,<3.10; 0.54.0 Requires-Python >=3.7,<3.10; 0.54.0rc2 Requires-Python >=3.7,<3.10; 0.54.0rc3 Requires-Python >=3.7,<3.10; 0.54.1 Requires-Python >=3.7,<3.10; 0.55.0 Requires-Python >=3.7,<3.11; 0.55.0rc1 Requires-Python >=3.7,<3.11; 0.55.1 Requires-Python >=3.7,<3.11; 0.55.2 Requires-Python >=3.7,<3.11; 1.21.2 Requires-Python >=3.7,<3.11; 1.21.3 Requires-Python >=3.7,<3.11; 1.21.4 Requires-Python >=3.7,<3.11; 1.21.5 Requires-Python >=3.7,<3.11; 1.21.6 Requires-Python >=3.7,<3.11
    44.72 ERROR: Could not find a version that satisfies the requirement onnxruntime>=1.19.0 (from versions: 1.15.0, 1.15.1, 1.16.0, 1.16.1, 1.16.2, 1.16.3)
    44.87 ERROR: No matching distribution found for onnxruntime>=1.19.0
    ```

  - onnxruntime not supporting Opset version >19; my model didn't explicitly define an opset version to default to the recommended version -> decision to re-export onnx model with Opset version 19
    - phase 4 folder was already stripped of dependencies necessary for model export --> switched back to phase3 foldern and virtual env
    - needed to re-install bape dependencies omegaconf, hydra-core, torchaudio, onnx, einops, matplotlib
    - exported new model version ending on `_opset18.onnx` -> copied to `../phase-4-serverless_deployment/onnx/`
    - fixed `MODEL_PATH = "super_param_estimator_opset18.onnx"`in `api.py`
    --> `docker run --platform linux/amd64 -p 9000:8080 bape-lambda` successful

- enable ffmpeg to convert non-wav to wav
  - add a function to audio_processor.py which takes ANY input and uses FFMPEG to transform it to an always predicatble wav format
    - _normalize_audio_with_ffmpeg
  - further down in audio_processor.py I need to update `transform_audio_to_spectrogram` so it 
    - expects any raw bytes from the upload instead of waiting to turn a file from path into bytes
    - always triggers `_normalize_audio_with_ffmpeg` function, which normalizes the input and gives it back as audio_array.

In my original function io.BytesIO(audio_bytes) loaded bytes from path but now audio_array is already in byte form and was loaded by librosa.load().
I can jump io.BytesIO() and librosaload() and send audio_array directly into the shape preprocessing:

```audio_processor.py
(…)
audio_array = _normalize_audio_with_ffmpeg(audio_bytes, target_sr=16000)

# Create 2D Mel Spectogram; shape -> (16, 2000)
spectrogram_2d = melspec_preprocessor(audio_array)

(…)
```
After running `docker build …` and `docker run …` another time, the app started successfully.  processed an mp3 and m4a file (see screenshot in `/onnx-acoustic/.local`).

Success: This is a working Serverless, Dockerized, Cross-Platform Audio Inference Engine, which
- accepts ANY audio format (M4A, WebM, MP3).
- sanitizes it to 16kHz Mono WAV.
- runs a complex PyTorch/ONNX model.
- does this in a stateless container that dies after it finishes.

With this setup step completed, I can move on to deploying the container image to AWS and make it available via API GW / Lambda.

Before, I deleted most of the BAPE_src files and anything related to model export which happens locally and must not be committed to the repo.

**onnx/ and src/ clean up: STILL NECESSARY FOR PHASE 3!**
=========================================================

Also, I refactored the shared upload function to display the name of the file upload isntead of input.wav or name it mic_recording.wav when it's not a file upload:

```index.html
(…)
        // --- SHARED UPLOAD FUNCTION ---
        async function upload(blob) {
            const formData = new FormData();

            // LOGIC: Check if it's a file with a name, otherwise default to 'mic_recording'
            let filename = 'mic_recording.wav'; 
            if (blob.name) {
                filename = blob.name;
            }
            // append with file name
            formData.append('audio_file', blob, filename);
        (…)
        }
(…)
```

## 3. Deployment

**What specific AWS service is designed to host Docker images so that Lambda can pull them?**
Elastic Container Registry ECR
- is an extension of both Elastic Container Services and Elastic Kubernetes Service

Features:
- lifecycle policies
- inspector / scan on push
- cross-region cross-acount replication


**Why would an enterprise choose ECR over Docker Hub for a proprietary ML model?**
AWS-managed instead of open-source, higher security standards through IAM credentials instead of username/password

**How does Lambda get permission to "reach into" that storage and pull your 900MB image?**
assumes an IAM role with ECR permissions

**What will happen if you deploy this container with the default settings?**
It will break because of insufficient memory (default is 128MB). The app itself is ~15MB and the necessary software packages slightly < 900MB.

**What memory setting will you start with to ensure the "Cold Start" (initial loading of the model) doesn't take 30 seconds? Justify your starting number.**
The phase 3 t3.small instance has 2GB RAM which we augmented with an additional 20GB EBS volume. This is not an option here.

Actually, I don't want to guess here and would like to run preliminary memory tests which tell us how much compute and memory we approximately need.

But having to guess, I would go with 4GB of RAM for the Lambda function.

### Updated Arch: container image, ECR, AWS infrastructure, CORS

```Mermaid
---
title: Phase 4 Architecture after containerization
---


graph TD
    subgraph User Client
    Browser[User Browser]
    end

    subgraph ECR
    bape-lambda[bape-lambda image]
    end

    subgraph "Static Frontend"
    S3_Bucket[S3 Bucket]
    end

    subgraph "Backend"
    LambdaFunctionURL[Lambda Function URL]
        subgraph Lambda-Service
        Lambda[Lambda Function, 
        Python 3.11 ]
        end
    end

    %% Flow 1: Loading the frontend
    Browser -- 1. GET index.html (including JS) --> S3_Bucket

    %% Flow 2: Using the app
    Browser -- 2. POST Audio 
    securley via SSL/TLS --> LambdaFunctionURL
    LambdaFunctionURL -- run inference session --> Lambda

    %% Flow 3: Fetching the image
    Lambda-Service -- get image via 
    IAM Role/Execution Role --> bape-lambda
```

### API Gateway or Lambda Function URL?

Looking into the Lambda Documentation the most prominently described options to invoke a Lambda fuction didn't even contain API Gateways.

**Lambda Function URLs vs API Gateway**

| Category | Lambda Function URL | API Gateway |
|---|---|---|
|Cost |no additional cost| cost per call; could be most expensive part of the app|
|Ease of use |easy, low effort setup| more complicated setup|
|Features |integrated with IAM |inegrated with most AWS services|
|Performance| very good | depends
|Security| default: HTTPS | default: HTTP 
|Timeout limits| 15 minutes | 29 seconds |

For elaborate use cases requiring detailed customization options on all aspects of the API an API Gateway is the more robust solution. In this situation where we look for price efficiency and will we need to fit our app into limited resources (especially time out durations), it only makes sense to opt for a Lambda Function URL.

### Hosting the front end from a public or private S3 bucket?

Setting the bucket to allow static webhosting requires the bucket to be publicly available.

I'm unsure about this decision. In the current situation I would accept having a public bucket but at the very first moment I share a link to the app I want the bucket to be private and allow all principals to get the index.hmtl (only getting, not listing, deleting, posting). Furthermore only I as the admin role should be allowed to full permissions on the bucket.

If I want the bucket to be private but the index.html still accessible I could do this via ACLs, CloudFront or a bucket policy.

### Memory and Performance

Since I didn't know exactly what compute and memory my image container would require, I ran the bape-lambda container another time and ran `docker stats`in another terminal window, where I could see that the app uses 100% of CPU at startup for a couple of seconds, during inference it reaches ~35% while processing a small mp3.
`docker stats` lists Memory Limit as 7,654GiB of which I use less than 10%.

```zsh
CONTAINER ID   NAME             CPU %     MEM USAGE / LIMIT     MEM %     NET I/O           BLOCK I/O         PIDS 
1deceae19ac3   exciting_fermi   0.48%     597.9MiB / 7.654GiB   7.63%     3.04MB / 11.3kB   29.5MB / 2.61MB   38 
```

### Drafting the CLI commands

***ECR/DOCKER***

*Create a repo and set automatic image scanning when pushing to the registry:*
```zsh
aws ecr create-repository \
--repository-name bape-ecr-repo \
--image-scanning-configuration scanOnPush=true
```
Copy AccountID from response for next command or safe to variable.

*Get ECR login and pipe to Docker; allowing Docker to pull/push images to ECR*
```zsh
aws ecr get-login-password | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.eu-central-1.amazonaws.com
```

*Tag and push the image to ECR*
```zsh
docker tag bape-lambda:latest $ACCOUNT_ID.dkr.ecr.eu-central-1.amazonaws.com/bape-ecr-repo:latest

docker push $ACCOUNT_ID.dkr.ecr.eu-central-1.amazonaws.com/bape-ecr-repo
```

***IAM***

An IAM role with the permissions to get the container image from ECR, assumable by the bape-lambda function, is required.

1. Trust policy: enables Lambda Service to assume role

[Trust Policy](../src/bape-trust-policy.json)

```src/trust-policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BapeLambdaTrustPolicy",
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

2. Permission policy: enables pulling image from registry

```src/bape_permissions-policy.json

{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BapeLambdaPermissionPolicy",
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "logs:CreateLogGroup", 
                "logs:CreateLogStream", 
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:ecr:<region>:<account-id>:repository/<repository-name>"
        }
    ]
}
```

Create this policy in IAM:

```zsh
aws iam create-policy \
--policy-name bape-permissions-policy \
--policy-document file://bape-permissions-policy.json
```
should return BAPE_PERMPOL_ARN

3. Create an Execution Role for the Lambda function

```zsh
aws iam create-role \
--role-name bape-lambda-exec-role \
--description execution role for bape-lambda-function \
--assume-role-policy-document file://src/bape-trust-policy.json
```

…copy $BAPE_EXECROLE_ARN, and attach the permissions policy to the role:

```zsh
aws iam attach-role-policy \
--role-name bape-lambda-exec-role \
--policy-arn BAPE_PERMPOL_ARN \
```

***Lambda***

Creating a function requires
- a deployment package (container image and its URI or zip file conatining function code)
  - code must be compatible with the target instruction set architecture of the function (`arm64` or `x86-64`, defaults to latter if not set)
- execution role


```zsh
aws lambda create-function \
--function-name bape-lambda-function \
--package-type Image \
--role $BAPE_EXECROLE_ARN \
--code <container image URI in ECR registry> \
--memory-size 2048 \
--timeout 60 \
#--ephemeral-storage 4096 \
--description Lambda function to run inference session against the BAPE onnx model
```

Create the Function URL

```zsh
aws lambda create-function-url-config \
--function-name my-bape-lambda-function \
--qualifier dev \
--auth-type NONE
# --cors-config {AllowOrigins="https://example.com"} // optional
```
---
---

```Mermaid
---
title: Ongoing Phase 4 Architecture
---


graph TD

    A@{ shape: diamond, label: "Decision" }

    CloudWatch[Cloud Watch]

    subgraph User Client
    Browser[User Browser]
    end

    subgraph ECR
    bape-lambda[bape-lambda image]
    end

    subgraph "Static Frontend"
    S3_Bucket[S3 Bucket]
    end

    subgraph "Backend"
    LambdaFunctionURL[Lambda Function URL]
        subgraph Lambda-Service
        Lambda[Lambda Function, 
        Python 3.11 ]
        end
    end

    subgraph IAM
    TrustPolicy[Trust Policy]
    ExecutionRole[Execution Role]
    PermissionPolicy[IAM Permission Policy]
    end

    %% Flow 1: Loading the frontend
    Browser -- 1. GET index.html (including JS) --> S3_Bucket

    %% Flow 2: Using the app
    Browser -- 2. POST Audio 
    securley via SSL/TLS --> LambdaFunctionURL
    LambdaFunctionURL -- run inference session --> Lambda

    %% Flow 3: Fetching the image
    Lambda-Service -- Policy-ExecutionRole --> bape-lambda
    Lambda-Service -- write logs --> CloudWatch

    %%Flow 4: 
    TrustPolicy --> ExecutionRole
```


IAM Role has:
Trust Policy: WHO can assume the role
Permissions Policy: WHAT can the role do (Services and Actions)?
