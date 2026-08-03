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

### 3.1. Updated Arch: container image, ECR, AWS infrastructure, CORS

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

### 3.2. API Gateway or Lambda Function URL?

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

### 3.3. Hosting the front end from a public or private S3 bucket?

Setting the bucket to allow static webhosting requires the bucket to be publicly available.

I'm unsure about this decision. In the current situation I would accept having a public bucket but at the very first moment I share a link to the app I want the bucket to be private and allow all principals to get the index.hmtl (only getting, not listing, deleting, posting). Furthermore only I as the admin role should be allowed to full permissions on the bucket.

If I want the bucket to be private but the index.html still accessible I could do this via ACLs, CloudFront or a bucket policy.

### 3.4. Memory and Performance

Since I didn't know exactly what compute and memory my image container would require, I ran the bape-lambda container another time and ran `docker stats`in another terminal window, where I could see that the app uses 100% of CPU at startup for a couple of seconds, during inference it reaches ~35% while processing a small mp3.
`docker stats` lists Memory Limit as 7,654GiB of which I use less than 10%.

```zsh
CONTAINER ID   NAME             CPU %     MEM USAGE / LIMIT     MEM %     NET I/O           BLOCK I/O         PIDS 
1deceae19ac3   exciting_fermi   0.48%     597.9MiB / 7.654GiB   7.63%     3.04MB / 11.3kB   29.5MB / 2.61MB   38 
```

### 3.5. CLI: Setting up the serverles infrastructure

***ECR/DOCKER***

#### 3.5.1. ECR: Create Repository

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

#### 3.5.2. DOCKER: Tag and push the image to ECR
```zsh
docker tag bape-lambda:latest $ACCOUNT_ID.dkr.ecr.eu-central-1.amazonaws.com/bape-ecr-repo:latest

docker push $ACCOUNT_ID.dkr.ecr.eu-central-1.amazonaws.com/bape-ecr-repo
```
*safe the container image URI to variable*:
`$BAPE_LATEST_CI_URI=$ACCOUNT_ID.dkr.ecr.eu-central-1.amazonaws.com/bape-ecr-repo:latest`


#### 3.5.3. IAM: Create trust and permisions policies (trust BAPE Lambda function and permit to pull from ECR and log to CloudWtach)

***IAM***

An IAM role with the permissions to get the container image from ECR, assumable by the bape-lambda function, is required.

1. Trust policy: enables Lambda Service to assume role
    [Trust Policy](../src/bape-trust-policy.json)

2. Permission policy: [Permission Policy](../src/bape-permissions-policy.json)

Create this policy in IAM:

```zsh
aws iam create-policy \
--policy-name bape-permissions-policy \
--policy-document file://src/bape-permissions-policy.json
```
should return BAPE_PERMPOL_ARN --> saved to variable


3. Create an Execution Role for the Lambda function

```zsh
aws iam create-role \
--role-name bape-lambda-exec-role \
--description "execution role for bape-lambda-function" \
--assume-role-policy-document file://src/bape-trust-policy.json
```
saved ARN to $BAPE_EXECROLE_ARN

…copy $BAPE_EXECROLE_ARN, and attach the permissions policy to the role:

```zsh
aws iam attach-role-policy \
--role-name bape-lambda-exec-role \
--policy-arn $BAPE_PERMPOL_ARN
```

#### 3.5.4. LAMBDA: Create function

***Lambda***

Creating a function requires
- a deployment package (container image and its URI or zip file conatining function code)
  - code must be compatible with the target instruction set architecture of the function (`arm64` or `x86_64`, defaults to `x86_64` if not set)
- execution role


```zsh
aws lambda create-function \
--function-name bape-lambda-function \
--package-type Image \
--role $BAPE_EXECROLE_ARN \
--code ImageUri=$BAPE_LATEST_CI_URI \
--memory-size 2048 \
--timeout 60 \
#--ephemeral-storage 4096 \
--description "Lambda function to run inference session against the BAPE onnx model"
```

AWS was rejecting this command with:

```zsh
An error occurred (InvalidParameterValueException) when calling the CreateFunction operation: The image manifest, config or layer media type for the source image 609662023678.dkr.ecr.eu-central-1.amazonaws.com/bape-ecr-repo:latest is not supported.
```

A quick search on the Error made me [learn, that docker exports more modern image versions, including features not supported by AWS Lambda.](https://medium.com/@kvendingoldo/fix-invalidparametervalueexception-for-aws-lambda-docker-images-built-by-github-actions-4369468d52e0)


So I had to strip these features (`--provenance=false --sbom=false`) from the build. `tag` the latest build and `push`again.

```zsh
docker build --platform linux/amd64 --provenance=false --sbom=false -t bape-lambda .

docker tag bape-lambda:latest $ACCOUNT_ID.dkr.ecr.eu-central-1.amazonaws.com/bape-ecr-repo:latest

docker push $ACCOUNT_ID.dkr.ecr.eu-central-1.amazonaws.com/bape-ecr-repo:latest
```


#### 3.5.5. LAMBDA: Create the Function URL and debug `403: Forbidden`

```zsh
aws lambda create-function-url-config \
--function-name bape-lambda-function \
--auth-type NONE
#allow all origins
--cors AllowOrigins="*"
```

The resulting live URL responded with:
```
{"Message":"Forbidden. For troubleshooting Function URL authorization issues, see: https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html"}
```

Following the link I learned that the rescource-based poilcy of the Lambda function mus allow any Principal permission to `lambda:InvokeFunctionUrl` and `lambda:InvokeFunction`

Adding the permissions via CLI:

```zsh
aws lambda add-permission \
--function-name bape-lambda-function \
--statement-id UrlPolicyInvokeURL \
--action lambda:InvokeFunctionUrl \
--principal "*" \
--function-url-auth-type NONE

aws lambda add-permission \
--function-name bape-lambda-function \
--statement-id UrlPolicyInvokeFunction \
--action lambda:InvokeFunction \
--principal "*" \
--invoked-via-function-url
```

--> went from 403:Forbiden to 502:Bad Gateway - Internal Server Error.

As I wanted to see the CloudWatch logs for the error, I realized faulty `bape-permissions-policy.json` because I could not see any Log Groups, when I tried `aws describe-log-groups`. 

Edited the policy and created a new version:

```zsh
aws iam create-policy-version \
--policy-arn $BAPE_PERMPOL_ARN \
--policy-document file://src/bape-permissions-policy.json \
--set-as-default
```

Triggered the Lambda Function URL again and tried again to get the logs but the server responded with a `502 Bad Gateway Internal server error`.

- Was trying for least privilege: ecr auth token only for one specific repo

- Decision: fix custom, least privilege policy or use aws managed policy?

--> Fix custom policy to maintain least privilege strategy:

Initially the policy allowed `ecr:GetAuthorizationToken` only for the specific `bape-ecr-repo`, which I changed to `*`.

Also, I edited the policy to be structured in three different statements: `AllowECRAuth`, `AllowECRPull` and `AllowLogging`:

[src/bape-permissions-policy.json](../src/bape-permissions-policy.json)

Next, another `aws iam create-policy-version …` updated the policy in IAM.

The next curl command still failed but succeeded to create a CloudWatch Log Group.
```zsh
❯ curl https://7ng4jbdvj2cd4s7ewneapjwaai0hyilw.lambda-url.eu-central-1.on.aws/

Internal Server Error%

❯ aws logs describe-log-groups

{
    "logGroups": [
        {
            "logGroupName": "/aws/lambda/bape-lambda-function",
            "creationTime": 1771251906628,
            "metricFilterCount": 0,
            "arn": "arn:aws:logs:eu-central-1:609662023678:log-group:/aws/lambda/bape-lambda-function:*",
            "storedBytes": 0,
            "logGroupClass": "STANDARD",
            "logGroupArn": "arn:aws:logs:eu-central-1:609662023678:log-group:/aws/lambda/bape-lambda-function"
        }
    ]
}
```
![Cloud Watch Logging](screenshots/2026-02-16_CloudWatch_tail.png "CLoud Watch Lambda Function tail")


#### 3.5.6. CLOUDWATCH: Debugging

Several findings in Logs:

```zsh
2026-02-16T15:41:45.743000+00:00 2026/02/16/[$LATEST]9747eac163aa44aca4abac629f3f4225 INFO lambda_web_adapter: app is not ready after 2000ms url=http://127.0.0.1:8080/
```
Dockerfile edit to increase the timeout of the lambda function:
```Dockerfile
ENV READINESS_CHECK_TIMEOUT=30
```


```zsh
2026-02-16T15:41:46.000000+00:00 2026/02/16/[$LATEST]9747eac163aa44aca4abac629f3f4225 /var/lang/lib/python3.11/site-packages/joblib/_multiprocessing_helpers.py:44: UserWarning: [Errno 13] Permission denied.  joblib will operate in serial mode
```
For this I found two relevant sources:

[Python multiprocessing: Permission denied](https://stackoverflow.com/questions/2009278/python-multiprocessing-permission-denied)
[Note on Joblib with Docker](https://gist.github.com/harusametime/f8b05719d63b56148275997fc6f3d175)

I had to redefine the `JOBLIB_TEMP_FOLDER`:

```Dockerfile
ENV JOBLIB_TEMP_FOLDER=/tmp
```
- Traceback: 

```zsh
2026-02-16T15:41:46.035000+00:00 2026/02/16/[$LATEST]9747eac163aa44aca4abac629f3f4225 Traceback (most recent call last):
2026-02-16T15:41:46.035000+00:00 2026/02/16/[$LATEST]9747eac163aa44aca4abac629f3f4225 File "/var/lang/bin/uvicorn", line 6, in <module>
2026-02-16T15:41:46.035000+00:00 2026/02/16/[$LATEST]9747eac163aa44aca4abac629f3f4225 sys.exit(main())
```

```zsh
2026-02-16T15:41:46.040000+00:00 2026/02/16/[$LATEST]9747eac163aa44aca4abac629f3f4225 raise RuntimeError("cannot cache function %r: no locator available "
(…)
2026-02-16T15:41:46.040000+00:00 2026/02/16/[$LATEST]9747eac163aa44aca4abac629f3f4225 raise RuntimeError("cannot cache function %r: no locator available "
```

The error RuntimeError: `cannot cache function... no locator available comes from Numba.`

Context: librosa uses numba to speed up audio math by compiling it into machine code on the fly (Just-In-Time compilation).
The Problem: Once numba compiles a function, it tries to save a "cache" file to the disk so it doesn't have to compile it again next time.
The Conflict: By default, it tries to write this cache inside the Python library folder (/var/lang/lib/...). In Lambda, that folder is read-only.
The Result: numba panics because it can't find a writable "locator" to save its work, and it crashes your entire Uvicorn process.
The Solution: Redirecting the Cache
Just like we did with joblib, I need to tell numba that the only place it is allowed to "write" its cache is the /tmp folder.
For this I redefine `ENV NUMBA_CACHE_DIR` in my Dockerfile:

```Dockerfile
ENV NUMBA_CACHE_DIR=/tmp
```
**Rebuilding, pushing the container image > rerun the lambda function url**

Again, the startup failed and the joblib error reappeared. Also, even a timeout increase to 60 seconds wasn't enough:
```zsh
65752135-93e2-4cca-9fd7-635695f2b06a    Duration: 60000.00 ms   Billed Duration: 60000 ms       Memory Size: 2048 MB    Max Memory Used: 610 MB    Status: timeout
```
--> The new `READINESS_CHECK_TIMEOUT` variable was irrelevant because I set it to 60 seconds already when creating the Lambda function (see 3.5.4. Creating the Lambda function)

Based on this I wanted to check if the ENV variables never reach the code or if `joblib` was running out of memory (though logs reported only 610MB of 2048MB max usage).


***Check variable settings***

- edit api.py to print the variables to make sure env variables are set correctly

```api.py
print(f"Debug: NUMBA_CACHE_DIR is {os.environ.get("NUMBA_CACHE_DIR")}")
print(f"Debug: JOBLIB_TEMP_FOLDER is {os.environ.get("NUMBA_CACHE_DIR")}")
```
(-> tag and push container image afterwards)

With these steps I learned about the "12-Factor App" principle, which states that configuration should be stored in the environment, while, here, I bake these variables into the Docker file. 
In AWS it's an integrated option (required?) to define `--environment` variables, which is the standard way and allows to change variables without rebuilding the container image over and over.

**Rerun with increased memory and timeout limit**
```zsh
aws lambda update-function-configuration \
--function-name bape-lambda-function \
--memory-size 4096 \
--timeout 120
```

Account was sandboxed to a 3008 MB quota, which could be increased by sending in a support ticket.
For now, I use what I have and increase timeout even more, to 180.

***SUCCESS***
After a long startup time of ~16 sec the app loaded and porcessed uploaded and recorded input successfully.

### 3.6. Feedback, requirement updates, fixes and finishing edits

I shared the working Lambda Function URL with my collaborator who was very happy with the basic functionality and immediately started to ask questions and make suggestions, which I wrote down

- cold start duration

- update onnx model

- evolve from "1-moment" result to time-based and eventually real-time inference

  - important output, `estimated parameters` is not time-based but generates 21 values reagrdless of input length. These 21 values are a 7x3 matrix in which a triple always describes
  1. the estimation range bottom
  2. the actual estimation
  3. the estimation range top

  - --> single output (as is) the model assumes that the room characteristics, source position etc don't change
    - --> things become interesting when the model can produce a time-series consisting of single-outputs --> time interval or window defined yet.

- possibility to download the exact input the model receives is necessary to evaluate onnx model output
  - spectrogram which is generated at the beginning of our app and which serves as input for the inference session
  - preprocessed audio

#### 3.6.1. Update onnx model
  - the resulting JSON displayed on the frontend triggered the question which exact weights were used for the onnx model
  - I was able to quickly look into the `MODEL_WEIGHTS_PATH` variable in the `param_estimator-onnx_exporter.py and identify the exact model.pth version I used
  - collaborators suspicion that it's not using the `2025-11-18-17-40-57` version were confirmed

  Quick Fix — Reexport model, update Docker Image without caching, update Lambda function code:

  - made edits (paths and model config) to [param_estimator-onnx_exporter.py](/phase-3-proper-infra/onnx/param_estimator-onnx_exporter.py) in order to export a new model

  Next, I wanted to update the container image on ECR and rerun the Lambda Function URL with the adjusted onnx model, but failed: In the resulting JSON the model path was still the old and I learned that Lambda is not automatically pulling the new image in order to prevent broken pushs.
  So my guess was that I needed to manually tell Lambda to pull the current image:

```zsh
aws lambda update-function-code \
--function-name bape-lambda-function \
--image-uri $ACCOUNT_ID.dkr.ecr.eu-central-1.amazonaws.com/bape-ecr-repo:latest
```

  But this also didn't fix the issue, so I checked my local build and ran
```zsh
docker run --platform linux/amd64 -p 9000:8080 bape-lambda:latest
```

  Running the app on localhost still returned the old model path.
  I needed to make sure docker was not reusing cached information for its build and I needed to start giving the build versions more descriptive name and most importantly changing names so I don't overwrite functional versions by accident.

```zsh
docker build --no-cache --platform linux/amd64 -t bape-lambda:2025-02-17-updated-onnx .
```
This built a new container image which used the corrected model path:

```zsh
❯ docker run --platform linux/amd64 bape-lambda:2025-02-17-updated-onnx cat api.py | grep "onnx/"
MODEL_PATH = "onnx/super_param_estimator_opset18_2025-11-18_17-40-57.onnx"
```

So I tagged the new version, pushed it to ECR and told Lambda to update the function code:

```zsh
docker tag bape-lambda:2025-02-17-updated-onnx $ACCOUNT_ID.dkr.ecr.eu-central-1.amazonaws.com/bape-ecr-repo:2025-02-17-updated-onnx

docker push $ACCOUNT_ID.dkr.ecr.eu-central-1.amazonaws.com/bape-ecr-repo:2025-02-17-updated-onnx

aws lambda update-function-code \
--function-name bape-lambda-function \
--image-uri $ACCOUNT_ID.dkr.ecr.eu-central-1.amazonaws.com/bape-ecr-repo:2025-02-17-updated-onnx
```

This threw an error I encountered already earlier: Docker builds the container image in the OCI Format which Lmbda doesn't support (also see 3.5.4.)

```zsh
An error occurred (InvalidParameterValueException) when calling the UpdateFunctionCode operation: The image manifest, config or layer media type for the source image 609662023678.dkr.ecr.eu-central-1.amazonaws.com/bape-ecr-repo:2025-02-17-updated-onnx is not supported.
```

I needed to rebuild and strip the `provenance` and `sbom` feature:

```zsh
docker build --no-cache --platform linux/amd64 --provenance=false --sbom=false -t bape-lambda:2025-02-17-updated-onnx .
```
and push again to ECR.

Debugging successful — the Lambda function responds with a JSON referencing the correct onnx model file.

#### 3.6.2. Cold start duration: 

Double penalty by:
  1. Lambda pulling a 900MB image from ECR, creating a container and allocating memory
  2. Once the container is live my Python code starts with loading heavy libraries (librosa, torch)

Quick Fix – Separation of concerns: 
  1. load static assets from S3 / CloudFront --> frontend instantly available
  2. Wait time occurs when file / recording is processed --> should feel more acceptable

##### 3.6.2.1. Updated Traffic Flow

```Mermaid
---
title: Updated Traffic Flow with Separation of Concerns
---

graph LR

    subgraph Client
    Browser[User]
    end

    subgraph Lambda
        LambdaFunctionURL[Lambda Function URL]
        LambdaFunction[Lambda Function]
    end

    subgraph CloudFront
    CFDistribution[CloudFront Distribution]
    end

    subgraph S3
        subgraph S3Bucket
            index[static index.html frontend]
        end
    end

    %% Frontend Flow:
    Browser -- 1. calls CloudFront URL --> CFDistribution -- 2. OAC entity trusted by private bucket policy --> index

    %% Backend Flow:
    Browser -- 3. uploads/records input via --> CFDistribution --> LambdaFunctionURL -- Function URL allows CORS from CloudFront URL--> LambdaFunction
    LambdaFunction -- 3. runs inference session / serves results --> Browser
```

##### 3.6.2.2. CloudFront considerations

As I expereinced in phase 3 using self-signed certificates, browsers see HTTP as insecure context and only allow mic access via HTTPS as a security measure so that the mic signal can't be intercepted and decrypted by third parties. CLoudFront automatically handels HTTPS certifcates and thereby ensures a secure context, thus enabling `navigator.mediaDevices.getUserMedia`.

I don't want to make my static project files or the bucket containing them public, so CloudFront will need permissions to access the private bucket. This will be established via an Origin Access Control entity which the resource-based policy of the bucket will grant permissions to `S3:getObjects`, maybe more.

##### 3.6.2.3. CLI: Separation of concerns 
Create
1. the origin

```zsh
aws s3api create-bucket \
--bucket bape-lambda-static-frontend \
--create-bucket-configuration LocationConstraint=eu-central-1

aws s3api put-public-access-block \
--bucket bape-lambda-static-frontend \
--public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

2. the identity

```zsh
aws cloudfront create-origin-access-control \
--origin-access-control-config Name=LambdaFrontendOAC,SigningProtocol=sigv4,SigningBehavior=always,OriginAccessControlOriginType=s3
```

3. the distribution

This is a first step into Infrastructure as Code: since CLoudFront doesn't have a flag to identify the OAC, I need to pass in a JSON which also contains the setting of other flags necessary like `--origin-domain-name` or `--default-root-object`.

See [BAPE Lambda distribution config](src/bape-lambda-distribution-config.json).

```zsh
aws cloudfront create-distribution \
--distribution-config file://src/bape-lambda-distribution-config.json
```

4. the resource-based bucket policy

see [s3-bape-frontend-policy.json](src/s3-bape-frontend-policy.json)

```zsh
aws s3api put-bucket-policy --bucket bape-lambda-static-frontend --policy file://src/s3-bape-frontend-policy.json
```
***Versioning the monolith***
Since I'm updating the `index.html` of the functional Lambda monolith version, I'm tagging the container image on ecr with `:v1-monolith`, before updating the path. Also, I copy `index.html` from `static/` to `frontend/index.html` before updating the path and leave `static/index.html` as is so that it can still be referenced by `v1-monolith`.

As the index.html cached on the CloudFront distribution needs an absolute path when triggering the `acou-vec/generate` function:

```JS
const response = await fetch('/acou-vec/generate', { method: 'POST', body: formData });
```
must become
```JS
const response = await fetch('https://7ng4jbdvj2cd4s7ewneapjwaai0hyilw.lambda-url.eu-central-1.on.aws/acou-vec/generate', { method: 'POST', body: formData });
```

***Copy static/index.html to the s3 bucket***
```zsh
aws s3 cp frontend/index.html s3://bape-lambda-static-frontend/index.html
```

Resulting CloudFront URL [https://d3ecws6p2nrrjd.cloudfront.net/](https://d3ecws6p2nrrjd.cloudfront.net/) // Frontend and backend separated


Now, the frontend loads instantly and only the upload button triggers the Lambda Function URL, which makes the Upload seem to take forever, because it`s actually creating the container and booting the app and it's dependencies.

The fact that this the Lambda function is reachable from here without explicitly giving Lambda any information about the CloudFront distribution, must worry us: 
In *3.5.5. Create the Function URL and debug `403: Forbidden`* I set the flag `--cors AllowOrigins="*"`, which is only acceptable during dev and test because it allows *any* actor to call the function from *anywhere*. 

So I update the function-config:

```zsh
aws lambda update-function-url-config --function-name bape-lambda-function --cors "AllowOrigins=["https://d3ecws6p2nrrjd.cloudfront.net"],AllowMethods=["POST"]"
```

Now, the Lambda function is deployed and accessible as

- (git tag: `phase-4.0-monolith`): monolith app (triggered frm the same source, the [Lambda Function URL](https://7ng4jbdvj2cd4s7ewneapjwaai0hyilw.lambda-url.eu-central-1.on.aws/))
- (git tag: `phase-4.1-decoupled`)a front- and backend-separated app (cross-source request only allowed from [CloudFront URL](https://d3ecws6p2nrrjd.cloudfront.net/))
- triggered from anywhere else than the Lambda Function or CloudFornt URL, cross-origin requests are blocked by policy

##### 3.6.2.X. More sustainable outlook: Provisioned Concurrency, Lambda SnapStarts and other options
  
  - look into provisioned concurrency (what is the price increase?):
  [Accurately estimating required provisioned concurrency for a function](https://docs.aws.amazon.com/lambda/latest/dg/provisioned-concurrency.html?sc_channel=sm&sc_campaign=Support&sc_publisher=REDDIT&sc_country=global&sc_geo=GLOBAL&sc_outcome=AWS%20Support&sc_content=Support&trk=Support&linkId=415993615#estimating-provisioned-concurrency)

  - compare to Lambda SnapStart (available for custom containers?):
  [Improving startup performance with Lambda SnapStart](https://docs.aws.amazon.com/lambda/latest/dg/snapstart.html)
    - supports Python 3.12 or later
    - not viable for images >512 MB

#### 3.6.3. Evolve to time-series processing

Currently, my `src/audio_processor.py` takes the whole file uploaded or recorded and gives one result. 21 numbers describing one spatial setting of the recording, in 7 estimated parameters, each with a lower and an upper estimation range, adding up to 21 numbers.

In order to make spatial changes, like the source of sound changing position, recoginzable, we need to slice recordings into smaller windows, which our function processes continually. A Sliding Window Processor.

Before we write code, we must define the parameters of the slice.

The Constraints:
- Model Input: ONNX model expects a specific tensor shape `([1, 1, 16, 2000])`.
- Sample Rate: 16,000 Hz.
- Spectrogram Config: The `melspec_preprocessor` maps audio samples to spectrogram frames.

The Design Questions (notes for Decision Log):

Window Duration: How many seconds of audio correspond to one inference pass?
- model takes a spectrogram of width 2000. hop size, the size of one analysis step/frame on the spectrogram, is 32.  
  2000 frames * 32 samples/frame = 64000 samples. 64000 samples / 16000 samples/second = 4 seconds.

- This determines the minimum chunk size the model processes at once.

- When we move to the next window, an overlap creates a smoother graph but increases the compute time

#### 3.6.4. Make exact model inputs available

##### 3.6.4.1. Code and script edits

- edited [`audio_processor.py`](src/audio_processor.py) to 
  - import `matplotlib` and set the colormap to AGG
  - encode the ffmpeg output bytes to Base64 and return the string along with `audio_array`, the input to `transform_audio_to_spectrogram`
  - include another helper function `generate_spectrogram_image`, which uses `matplotlib` to render `spectrogram_2d`, a preprocessed state of the final model input `spectrogram_4d`, safe the rendering to a buffer instance, encode it also to Base64 and return `spectrogram_b64`
  - augment the `transform_audio_to_spectrogram` function to return  `clean_wav_b64`, `spectrogram_b64`, `input_duration` in addition to `spectrogram_4d`.

- edit api.py to expect the new outputs of `audio_processor.py`, JSON now also returns:
  - input length
  - spectrogram PNG as Base64 string
  - input WAV as Base64 string

- edit `frontend/index.html` (must be updated on S3) to include <audio> and <img> elements which display the decoded Base64 strings

##### 3.6.4.2. Adding matplotlib
When importing matplotlib an update of requirements.txt was necessary, but if I would compile my requirements.in on my machine the docker container would run into dependency errors. Therefor I ran a Docker container with the environment of our bape lambda container, mapped my project folder to a folder of the Docker container, compiled my requirements.in on the container instance and write the requirements.txt back to my hard drive:

```zsh
docker run --rm \
-v $(pwd):/var/task \
--entrypoint /bin/bash \
public.ecr.aws/lambda/python:3.11 \
-c "pip install pip-tools 'numpy<2.0.0' && pip-compile requirements.in"
```

When encountering several errors during container builds, I learned that build errors are often caused because no Python Wheels are found for package installation, leading to the attempt to compile from Source Code, but containers are designed to be light weight and don't have compilers on board.
So I can do a manual audit of package versions in pypi:

`contourpy` tried to install it's 1.3.3. version but it failed.

1. I go to PyPI Contourpy 1.3.3 Files.
2. I look for manylinux. I see they exist, but maybe they require manylinux_2_28.
3. I then check other versions until I look into PyPI Contourpy 1.2.1 Files.
4. I see version 1.2.1 has wheels for manylinux2014. This is an older standard.

The Insight: Older standards have wider compatibility. By choosing a version that supports an older Manylinux standard, I am guaranteeing it will install without a compiler in a restricted environment like Lambda.

##### 3.6.4.3 Script and frontend edits, pushing to ECR and GitHub

With the backend starting up correctly with Matplotlib I was able to edit mostly the `audio_preprocessor.py` to
- encode the read audio bytes from Upload/Recording to Base64 and return along with `spectrogram_4d`
- add `generate_spectrogram_image()` helper function which uses matplotlib to rendert a spectrogram, safe it to a buffer and encode it toBase64
  - call this function during `transform_audio_to_spectrogram()` to create the spectrogram image and add it to the return
- add `input_duration` to return statement

Further edits:
- updated Dockerfile to source ffmpeg build from another container image instead of from a URL, which suddenly was unavailable during bug fixing
  - this also came down to a cleaner Dockerfile
- updated `model_processor.py`
- update api.py to include the new return information from `audio_processor.py`
- dependency wrangling when importing matplotlib: prevent Lambda from trying to compile packages from source not available as py wheels 
  - find best compatible versions on pypi
- edit frontend to display audio player and spectrogram

To get the updated version running on the Lambda function I had to build a new updated image and make sure no old information is cached and that it's correctly tagged in ECR and pulled by the Lambda function.

When this worked I pushed all changes to GiHub with dedicated commit meassges to the changed files. Afterwards I (accidentally) tagged the version as 2.0 and pushed it to GiHub. Unfortunately I had this tag already so it was overwritten. This wasn't a big problem since the version changes where minor from a cloud engineering perspective.
As described in 3.6.5.1., I later tagged this committed version as `phase-4.2-audio-and-spectrogram-output`.

#### 3.6.5. Further learnings and edits

##### 3.6.5.1. Serverless Machine Learning Inference : Cold starts
The resulting app is a major improvement in comparison to the phase-3-infrastructure in terms of cost and maintanance BUT even though the Lambda function itself delivers inference results instantaneously, the cold-start times are not acceptible for a frontend suggesting immediate or even real-time results.
Fixing this with Provisioned Concurrency (with scheduled down and up times), setting up EventBridge events to ping the function regularly or considering Lambda Snap Starts, showed me the constraints of using Lambda functions for (near) real-time inference.
The boot time of the Lambda function of 15-30 seconds is actually good but not adequate for a user experience suggesting to be "always on". In a setting where the user doesn't wait for the results, i.e. expecting them per mail, this would be much better, but as the app is perspectively meant to be a real-time inference machine, which still has acceptible cost, scaling and latency constraints, I plan on finding such a solution in phase 5.

I added a pseudo-progress response from the frontend when finishing this phase.

##### 3.6.5.2. Versioning and git Tagging
I clearly felt an increase in speed while iterating the app and producing incremental improvements. Initially I planned on having 5 different deployment versions after all but at this point I wanted a tighter handle on versions and make them available for demonstration and comparisons in rertrospect/during job application process.

I used `git log …` and `git tag …` to get an overview of my git versioning history and copy the commit identifiers of versioning milestones, to which I added

- phase-1.0-local
- phase-2.0-naive
- phase-3.0-infra
- phase-4.0-monolith
- phase-4.1-decoupled
- phase-4.2.audio-and-spectrogram-output

##### 3.6.5.3. Solving memory constraints with Pre-Signed URLs // Claim Checking

As the buffer of the Lambda function is limited to 6 MB, the function crashes already with smaller files like a 4MB mp3.
Also, encoding the model WAV and spectrogram input in the backend, send it to the frontend and encode it with JavaScript puts a lot of overhead on the frontend.

Storing the results in S3, configuring an adequate lifecycle policy and making them available via time-limited Pre-Signed URL
- takes the load from the frontend
- makes files instantaneously available

For this, I will 
- import boto3 to my api.py
- create a function to upload artifacts to S3 and make them available via Pre-Signed URL, which will
  - use the ready-made `generate_presigned_url()` and `put_object()` functions of boto3's S3 client
  - use `uuid` to create distinctive object names
- update index.html to source the links from the functions results and display them on the frontend

At this point I need to think this out aloud:

Right now my `audio_processor.py` defines the main function `transform_audio_to_spectrogram()` (which actually isn't named very well anymore since it's doing more) and helper functions and classes required by the main function.
It reurns the spectrogram tensor, the normalized wav in Base64 encoding, the spectrogram as png encoded in Base64 and the input duration.

In the `api.py` the asyncronous function `generate_vector_endpoint()` (also a suboptimal name I think) uses FastAPIs `UploadFile`, which are checked for the correct content type and then read into memory. Then the `transform_audio_to_spectrogram()` is called which returns the beforementioned results, one of which, `audio_spec` is the actual input for the onnx model, which is then invoked with `processor.generate_vector(audio_spec)`, an instance of the `AcousticModelProcessor` class (including the `generate_vector()` function) from `model_processor.py`.

###### Where can we intercept the normalized audio and spectrogram png?

Now the question is where we can intercept the cleaned WAV and spectrogram PNG – before / without Base64 encoding – upload it to S3 with a unique name and then generate a presigned URL and return it back.

As this is not a part of audio preprocessing nor model processing our new function `upload_artifact_and_get_presigned_url()` will be defined in api.py
It takes in the result of `generate_spectrogram_image()` which currently is `img_b64` and `clean_wav_b64`, the result of `_normalize_audio_with_ffmpeg`.

###### Get rid of Base64 encoding

I will change both functions to not decode the wav and png to Base64, like:

```Python
# audio_processor.py:
# (…)
def _normalize_audio_with_ffmpeg(…)
#(…)
        # 5. Get the cleaned WAV for the frontend ("r"eading as "b"inary)
        with open(output_path, "rb") as f:
            clean_wav=f.read()
            
        return audio_array, clean_wav

# (…)
def generate_spectrogram_image(spectrogram_2d: np.ndarray) -> str:
    """
    Converts the 2D Spectrogram (a numpy array) into a PNG.
    """
    plt.figure(figsize=(10,4))

    # Render the spectrogram using matplotlib's imshow instead of librosa's display
    # imshow is lighter and doesn't require importing librosa.display
    # origin='lower' ensures low frequencies are at the bottom
    # cmap defines colormap, viridis is the default
    plt.imshow(spectrogram_2d, aspect="auto", origin="lower", cmap="viridis")
    plt.axis('off') # hide axis for cleaner look
    plt.tight_layout(pad=0) #padding layout

    #save the plot to memory buffer
    buf=io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
    plt.close() #close plot to save memory
    spectrogram_png=buf.getvalue()
    return spectrogram_png #returns png in bytes
```

then in the `transform_audio_to_spectrogram()` function in the same script, I update the variables:

```Python
# (…)
        # spectrogram rendered in matplotlib as png / in bytes 
        spectrogram_png=generate_spectrogram_image(spectrogram_2d)
        print("Spectrogram rendered in matplotlib as png.")
# (…)
        # Return the final tensor: Innference input as array (for model), as wav and png (for user) 
        # print(f"Data type is:{spectogram_4d.dtype}")
        return spectrogram_4d, clean_wav, spectrogram_png, input_duration
```

###### Setting a lifecyle policy on the `bape-static-frontend` S3 bucket
Meanwhile for lifecycle configurations to take place I need to create and set a poilcy:

`src/lifecycle-configuration-policy.json`:

```JSON
{
  "Rules": [
    {
      "Expiration": {
        "Days": 1
      },
      "ID": "bape-result-lifecycle-policy",
    }
  ]
}
```

0.000695 is a little more than a minute and I wonder hy I cant set minutes or seconds but only days!?
Anyways… I put the bucket lifecycle policy:

```zsh
aws s3 api put-bucket-lifecycle-configuration \
--bucket bape-lambda-static-frontend \
--lifecycle-configuration file://src/lifecycle-configuration-policy.json
```

###### Add function to upload files and generate presigned URLS to `api.py`
Now I build the new function in `api.py`:

```Python
(…)
# added dependencies
import boto3
from botocore.exceptions import ClientError
import uuid
(…)

# rough draft:
# define function
    # initialize s3 client
    # put bytes to s3 (not upload file) as an object, named individually via uuid
    # generate presigned url
# call function on preprocessed audio and spectrogram

def upload_artifact_and_get_presigned_url(file_bytes: bytes, object_key: str, content_type:str):
    """
    Upload a file to an S3 bucket, if upload succeeds, return presigned URL    
    """

    # set bucket as env var
    bucket_name="bape-lambda-static-frontend"
    # initialize S3 client
    s3_client = boto3.client('s3')
    # Safe object to S3
    try:
        # 1. put_object for raw bytes
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=file_bytes,
            ContentType=content_type
        )

        # 2. Generate presigned URL
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_key},
            ExpiresIn=300,
        )
        return url

    except Exception as e:
        logger.error(f"S3 Bridge Error:{e}")
        return None
(…)
```
Later in api.py, in the `generate_vector_endpoint()` function, right before the inference happens, I call the function on the `clean_wav` and `spectrogram_png` output we redefined further up:

```Python
(…)
async def generate_vector_endpoint(audio_file: UploadFile = File(...)):
(…)
# 3. Preprocess audio input using modular function from audio_processor.py
    # intialize a preprocessing session variable for naming files
    session_id=str(uuid.uuid4())
    wav_key=f"results/{session_id}_input.wav"
    png_key=f"results/{session_id}_spectrogram.png"

    try:
        audio_spec, normalized_wav, spectrogram_png, input_duration = transform_audio_to_spectrogram(contents)
    except Exception as e:
        logger.error("Audio preprocessing failed for %s: %s", audio_file.filename, e)
        raise HTTPException(status_code=400, detail=f"Audio preprocessing failed: {e}")
    
    logger.info("Preprocessed audio shape: %s", audio_spec.shape)

# 4. Safe input to S3
# 4.1. Upload normalized audio to S3 and generate presigned URL
    try:
        wav_url=upload_artifact_and_get_presigned_url(normalized_wav, wav_key, "audio/wav")
    
    except ClientError as e:
        logging.error(e)
        return None

# 4.2. Upload to normalized audio to S3 and generate presigned URL
    try:
        png_url=upload_artifact_and_get_presigned_url(spectrogram_png, png_key, "image/png")
    
    except ClientError as e:
        logging.error(e)
        return None

    print(f"Spectrogram available via {png_url}. Normalized wav input available via {wav_url}. These links will time out after 1 minute. The objects will be deleted in 24 hours.")
```

We can then include the png_url and wav_url to our API response further down:

```Python
    return {
        "request_metadata": {        
            "filename": audio_file.filename,
            "input duration": f"{input_duration} seconds",
            "processing_time_ms": round(processing_time_ms, 3)
        },

        "preprocessed_inputs": {
          "png_url": png_url,
          "wav_url": wav_url
        },

        "inference_results": {

            "estimated_parameters": {
                "shape": list(estimated_params.shape),
                "values": estimated_params.flatten().tolist()
            },

            "quantiles": {
                "shape": list(quantiles.shape),
                "values": quantiles.flatten().tolist()
            }            
            }

        }
```

In the frontend/index.html I refactor the JavaScript to source the audio and png from the presigned URLs isntead of decoding them from Base64 sent within the API's JSON response

```JS
// (…)
            // append with file name
            formData.append('audio_file', blob, filename);

            try {
                const response = await fetch('https://7ng4jbdvj2cd4s7ewneapjwaai0hyilw.lambda-url.eu-central-1.on.aws/acou-vec/generate', { method: 'POST', body: formData });
                const data = await response.json();
                const result = data.preprocessed_inputs;

                // 1. Set the Audio Player source
                if (result.wav_url) {
                    document.getElementById('audio-player').src=str(wav_url);
                }
                // 2. Set the Spectrogram Image source
                if (result.png_url) {
                    document.getElementById('spectrogram-display').src=str(png_url);
                }

                resultArea.classList.remove('hidden');
                jsonResult.textContent = JSON.stringify(data, null, 2);
                statusText.innerText = "Success";
            } 
            
            catch (err) {
                statusText.innerText = "Failed";
                console.error(err);
            }
        (…)
```

Before testing the updates I …

… create a new version of the `bape-permissions-policy.json` and set it as default.

```zsh
aws iam create-policy-version --policy-arn $BAPE_PERMPOL_ARN --policy-document file://src/bape-permissions-policy.json --set-as-default 
```

… build and tag a new Docker image: 
```zsh
docker build --no-cache --platform linux/amd64 --sbom=false --provenance=false -t bape-lambda:2025-03-02_v3-s3-claim-check .
```

… creat a tag for ECR
```zsh
docker tag bape-lambda:2025-03-02_v3-s3-claim-check $ACCOUNT_ID.dkr.ecr.eu-central-1.amazonaws.com/bape-ecr-repo:2025-03-02_v3-s3-claim-check
```

… push tag to repo:
```zsh
docker push $ACCOUNT_ID.dkr.ecr.eu-central-1.amazonaws.com/bape-ecr-repo:2025-03-02_v3-s3-claim-check
```


- update the Lambda function code

```zsh
aws lambda update-function-code --function-name bape-lambda-function --image-uri $ACCOUNT_ID.dkr.ecr.eu-central-1.amazonaws.com/bape-ecr-repo:2025-03-02_v3-s3-claim-check
```

- update the frontend object in s3:
```zsh
aws cp frontend/index.html s3://bape-lambda-static-frontend/index.html
```


###### Testing the claim check

Calling the frontend via the Cloudfront URL, starting the model and running an inference with a 4.5MB mp3 which lead the function to break because of insufficient memory, now ran without complications and the JSON now included the PreSigned URLs.

But the contents failed to load (screenshot)["screenshots/2026-03-02_claim-echeck-test.png"]. When maually opening the Presigned URLS the API made the problem clear:

```XML
<Error>
<Code>AccessDenied</Code>
<Message>User: arn:aws:sts::609662023678:assumed-role/bape-lambda-exec-role/bape-lambda-function is not authorized to perform: s3:GetObject on resource: "arn:aws:s3:::bape-lambda-static-frontend/results/5dbe5aa5-aae9-4ca9-9047-8cc9aa1b189b_spectrogram.png" because no identity-based policy allows the s3:GetObject action</Message>
<RequestId>DJX492JDVT32GKK7</RequestId>
<HostId>tp9yJycSh/DpE15+t8ngYjUokodnZbGFoEKK0w7xJaxL9rnx/hm+HdlHO2sGnxm4jtwN6Df6EDFyl40I6B0btvP8UIPAlf4rQ+LyoVmMJHE=</HostId>
</Error>
```

So I needed to update the bape-permissions-policy.json to have S3:getObject permissions. This permission is inherited by the Presigned URLs.

Testing successful.

Minor frontend edits: simulate cold start progress.

##### 3.6.5.4. Moving on to a sliding processin window (Merge with 3.6.3)

---
feedback call 01-03-2026:
- real benefit from dynamic results

- quality of acoustic fingerprint is described in `quantiles`
- confidence in estimated parameters depends on quality of acoustic fingerprint

- received paper on March 3
---


To evolove to a dynamic app allowing for multiple related inference results, a timeline of estimated parameters, I need to 

- change the Python backend to run the inference on slices of the audio input, thus first slicing the audio input before processing all slices
- restructure the JSON response to include inference results with timestamps, this will be foundational for time-series
- visualize the results (wav-form, confidence (quantiles), time-based blindly estimated parameters)

***Defining the windows***
Overlapping input windows, i.e. 1-4 seconds, 3-7 seconds, 5-9 seconds instead of 1-4 sec, 4-8sec, 8-12 sec,…, will produce a smoother graph but will also increase the processing power required.

*Terms:*
- Temporal Resolution: The frequency of results (e.g., "One inference per second").
- Striding/Hopping: The distance the window moves between inferences.
- Inference Latency Per Window: The time it takes for one pass through the ONNX model.
- Confidence Envelope: The visual representation of the Quantiles around the Estimated Parameters.

I choose to use a temporal resolution of 1 inference per 4 seconds of input. Meanwhile the stride of the sliding window will be two seconds. This should double the compute of slicing the input into separate, non-overlapping 4 second inputs, because everything but the last and first two seconds will be processed twice.

```Mermaid

flowchart LR

A[audio_array]
C{transform_audio_to_spectrogram}
E[clean_wav]
F[spectrogram_png]

H{_normalize_audio_with_ffmpeg}
I{generate_spectrogram_image}
J{generate_vector}
K{upload_artifact_and_get_presigned_url}
L{melspec_preprocessor}

N[audio_spec/spectrogram_4d]
O[png_url, wav_url]
P[model outputs: estimated params, quantiles]
Q{generate_vector_endpoint}
R(Client)
S[API]

R -->|audio input| S

subgraph audio_processor.py
C --> H 
H --> E
C --> I --> F
C --> L
L -->|np.expand_dims| N
H --> A
A --> L
end

subgraph api.py
  S -->|audio_file| Q
  Q --> C
  N --> J
  E --> K
  F --> K
end

subgraph index.html
  J --> P
  K --> O
end
```


Pseudo-Code:
- define a function to slice audio into windows
  - define a window and stride size
  - define empty list `slices`
  - define empty list `timestamps`
  - loop through all possible values of `i` as long as `i` is in the range starting at 0 and ending on number of last sample; increment `i` by `stride_size`; repeat the following:
    - for each i, create a chunk:
      - set `start` to i
      - set `end` to i + window_size
      - define `chunk` as array from `start` to `end`
    - if the `chunk` is smaller than window size
      - define padding as (window_size - chunk_size)
      - update `chunk` to be padded at the end by defined padding, fill with constant value
    
    - for each i, append the chunk to the slices list
    - for each i, append a timestamp giving the start time in seconds
      - convert samples to seconds (i/16000)
      
    
    - return list of slices and list of timestamps

- in the preprocessing `transform_audio_to_spectrogram`, pass in the list of slices stack them vertically at axis=0


- I will use range(start, stop, step) to define slices 
  - as we don't talk about time in seconds but number of samples, 1 second consists of 16000 samples, thus the window is 64000 samples large
  - We start at 0, end at 64000 and step by 32000 samples (2 seconds):
  `range(0,64000,32000)`` -> I have to find out how this is defined when "moving"
  - when we have the normalized audio in byte samples we can slice it

```Python
def slice_audio_into_windows(audio_array: np.ndarray, sr: int = 16000):
  window_size = 4 * sr
  stride_size = 2 * sr

  total_size=audio_array.size

  for i in range(0, total_size - window_size + 1, stride_size):
    start = i 
    end = i + window_size
    slice = audio_array[start:end]


```

Then I would batch the result into one tensor and run the model once.
The api.py needs to be refactored to accomodate for the result of the batch inference session

#### 3.6.6. Refactoring / Renaming


## 4. Phase finish

### 4.1. What was done?

### 4.2. What was learned?

### 4.3. What's up next?

## X. Appendix

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

Lambda has:
Resource-based policy

AWS Orgainzations / IAM Identity Center:
- Service Control Policies (What services can users access?)