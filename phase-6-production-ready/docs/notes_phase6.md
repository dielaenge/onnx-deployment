# Notes Phase 6

**Duplicate from end of notes_phase5.md:**

> - Refactored terraform folder
 > My tf file structure was based on some best practices I found from Hashicorp but couldn't find again ad-hoc, so now I feel like we we are in transitiionig state. 
> I pciked apart the main.tf and created ecr.tf, ecs.tf, elb.tf, iam.tf, routing.tf, security-groups.tf, vpc.tf and vpc-endpoints.tf by copy pasting the according blocks from main.tf to the separate tf files.

> Before making the transition to phase 6 I wanted to do the rightsizing so I decided to go back to phase 5 on feat/container-orchestration (where the phase 6 folder is still in untracked status, though I added and pushed it to feat/production-ready, the phase 6 branch) and ran tf apply and then ran our build and deploy to ECS Action because before applying it was failing with Could not assume role with OIDC: No OpenIDConnect provider found in your account for https://token.actions.githubusercontent.com an dI don't know how much it added to failure but GitHub asked from which branch I wanted to run the workflow. FIrst I chose main. For the second run, after running tf apply I set this to feat/production-ready. The second run succeeded. I ran a couple of inferences with the 3.5MB mp3 and I got some numbers in container insights but I struggle to read them. I can see that not only one but two containers are in my cluster. The max CPU utilization I can see is around 36% and max Memory utilization around 20%

## Splitting main.tf

Switched back to `feat/production-ready` restructured files in `terraform/` to split bloated `main.tf`.

## Rightsizing task definition

Set `containerInsights setting` to `enhanced` in `bape_cluster` resource definition.

Set `aws_ecs_task_definition.task_definition_bape` to `cpu = 768` and `memory = 1024`.
  - `cpu = 768` and `memory = 1024` were not valid settings
  - `cpu = 1024` and `memory = 1024` were not valid settings
--> back to [documentation](https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_TaskDefinition.html#memory)

With the rough numbers from Container Insights (we used 36% of 1024 MB CPU, ~370MB, and 20% of 2048MB Memory, ~410MB), the amount of memory we give determnines the possible cpu size: to right size we must provide more than 256 MB cpu, 1024 like we did or 512 to save on resources. I opt for the latter for development. With a 512 MB CPU, we can set memory to 1024 (1 GB), 2048 (2 GB), 3072 (3 GB) or 4096 (4 GB).

I suggest going with 512 MB CPU, and 1024 MB Memory so that our measures are around 50% of maximum capacity

- zsh: `tf apply -target="aws_ecr_repo…`
- zsh: `tf apply`
- GitHub Actions: `build-and-deploy-to-ecs.yml` workflow, run on `feat/production-ready` branch, successful?

First try failed because `aws_iam_role.github_actions_role` was still conditioned to only access `feat/container-orchestration` branch.

Second try successful: CPU peaks at startup (~50%; `ort.InferenceSession`) and is easily doing bigger inferences (115 spectrograms / 3.5MB mp3 loads 30%), initializing the model and then keeps at around 40% memory while having the model cached and ready for inference.

--> TBD: Simulating traffic with [k6](https://k6.io/open-source/) or [artillery](https://www.artillery.io/docs)

--

## Breaking down the monolith pipeline

ATM each user upload is fully processed before another user can be served. So, if >1 users send an audio upload, before the second user is processed the system has to:

1. Receive the upload
2. Start FFmpeg and normalize audio
3. Create Spectrogram
4. Create two presigned S3-Links and upload normalized wav and spectrogram png
5. Slice the spectrogram and run inference iteratively on slices
6. Return JSON
--
7. Viz is rendered on frontend

This pipeline can induce time-out errors for waiting users (when? --> load testing).

I want to look for ways to decouple inference from upload and preprocessing


Decision: Async Decoupling Mechanism

| Criteria        | SQS + ECS | Step Functions | FastAPI Background | Comments |
|-----------------|-----------|----------------|--------------------|---------------|
| Cost            | The SQS queue itself will cost 0, but the Worker reading the queue requires a second ECS Fargate task running constantly to poll the queue, so per-session compute cost essentially doubles (API container + Worker container). In an apply/destroy model, this is pennies, in prod this can become a fundamental difference. Load Balancer and VPC currently most expensive  | 4000 state changes free; above: 0,25 USD / 1000 state changes; I assume we would have 2 state changes per entire function, so 2k calls/mth free |         0          |  |
| Complexity      | SQS is vastly simpler as it is just a buffer — push a JSON message to it, and another script pulls it. | Step Functions requires writing Amazon States Language (ASL) JSON to define state machines, managing input/output path transformations, and handling distinct IAM roles for every step. For a single-step background job, Step Functions is massive overkill. | low, so would add as a quick win |
| Fit for BAPE    | Best fit I see for splitting upload, preprocessing, generating presigned urls for generated wav / png and inference | Calling a Lambda function takes too long if cold-started, paying for warm functions exceeds ECS costs  | Nice to handle the current processing time more elegantly, but irrelevant to my cloud engineering skill set |
| Resume value    |   *****   |      ****      |          *         |

**Decision:** I tend to SQS because it suits or requirement for low latency while splitting the different application steps allowing me to better monitor the separate processes and eventually fine tune resources to the separate steps as need may arise.
BUT: We are aiming for a real-time application in this phase and using asynchronous decoupling (SQS) might counteract to the objective.

**Trade-offs accepted:** By choosing this, I am accepting that I'm not learning Step Functions at this point, but I think for my use case, step functions would not benefit Paul's experience at this point.

**Further thoughts:** If I understand correctly, we could improve the UX by making the call to our app a FastAPI Background Task and give the user a chance to learn more before results come in… that is, at this stage. 
BUT: a non-negotiable requirement for this phase is the real-time functionality… maybe if the cost structure requires it, we can make the real-time app a lambda function and possible cold starts are sort of moderated… If we go this way we have to mind the timeout limits and I have no idea if websockets can be part of a serverless lambda function.

**Other options researched:** Celery, the Python industry standard for async decoupling, but requires a Message Broker (like Redis or RabbitMQ) to hold the queues. Running Redis on AWS means ElastiCache, which has no free tier and costs ~$15/month minimum. SQS is serverless and free --> chose the AWS-native, cost-effective route over the traditional Python route. 

### Distributed vs. real-time app dilemma

A distributed app with SQS would look like this:

1. Client sends audio via REST API
2. API container processes upload (What does that mean? I just see that there's an upload function in the index.html JS and a read() function in the main.py)
3. Sends JSON notif to SQS queue ("Upload done.")
4. Worker Container pulls JSON
5. Worker Container transforms audio with ffmpeg, creates spectrogram, slices spectrogram, creates pre-signed urls, uploads transformed audio and spectrogram to S3 presigned url and runs inference loop
6. When done Worker COntainer sends JSON to other SQS queue ("Inference Done.")
7. Client polls SQS queue
8. When available, JSON result is sent to frontend (not saved to S3 or DynamoDB)

Decoupling means splitting synchronization and I need to understand if we are aiming to orchestrate separate tasks or choreograph dependent tasks.

In a real-time application synchronization is a must-have, esepcially when it's executing all the same steps in the same order in any form of use. So besides getting deeper insights on different processing steps, I don't see a benefit in decoupling task when aiming for a real-time application result.

BAsed on 
Pauls requirements: - real-time

Portfolio requirements:
- cloud engineering skills; can't tell if distributed architectures or streaming are more sought after, I would guess distributed architectures is a hotter topic but I don't know

I would decide on the "client"'s requirement
