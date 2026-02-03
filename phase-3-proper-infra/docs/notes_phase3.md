# Phase 3 – Proper (Standard?) Cloud Deployment – ONNX deployment evolution

## 0. Restructuring overall project in separate phase folders (Proper Cloud Deployment)

Before setting up the project folder for stage 3, I wanted to clean up the project structure and establish folders for each project stage, with their respective file versions at the end of each stage.

For this I displayed the versioneing tree with `git log --all --decorate --oneline --graph` and found out at which commits (`hashes`) Phase 1 and 2 ended.

I then created dedicated folders for phase 1 and 2.
As I learned from the versioning graph, the end of phase 1 was at commit `b5c9d1c` and I used `git archive …` to store this project state in the `phase-1-local_deployment` folder.

More specifically:
`git archive b5c9d1c | tar -x -C phase-1-local_deployment`

Explanation:
`git archive …`: This creates a new archive from all files of that specific commit.
`| tar`: Pipe to tar, which…
`-x -C phase-1-local_deployment`: istructs tar to extract (`-x`) the piped archive and change (`-C`) it to the `phase-1-…` folder.

As we are about to start with stage 3, we can still take a snap shot of our latest project version (`HEAD`) and store it to the stage 2 folder:
`git archive HEAD | tar -x -C phase-2-manual_cloud_deployment`

I then removed all files but README.md and .gitignore (`--cached` tells git to also remove them from tracking) from the root folder:
`git rm -r --cached api.py cli.py docs dummy_acoustic_model.onnx requirements.txt requirements-dev.txt src`

and deleted them for definitely, not only from tracking:

```zsh
rm -rf api.py cli.py dummy_acoustic_model.onnx requirements.txt requirements-dev.txt src temp docs
```

After running `tree -L 3` to check the project structure, I committed and merged the `refactor/project-structure` branch to main:

```zsh
git add .
git commit -m "refactor: Organized project folder(s) into self-contained snapshots of each phase within the bigger project"
git checkout main
git merge refactor/project-structure
git push origin main
# branch not yet deleted – command: git branch -d refactor/project-structure
```

## 1. Initializing Phase 3 and embedding BAPE (todo: translate to decision_log)

### 1.1. Switching to `feat/proper-AWS-deployment` branch and create phase 3 folder

On `main`, pull all changes.
Switch to `feat/proper-AWS-deployment` branch.

Create Phase 3 folder and decision log.

copy recursively:

- `phase-2-manual_cloud_deployment/api.py`
- `phase-2-manual_cloud_deployment/src/`
- `phase-2-manual_cloud_deployment/dummy_acoustic_model.onnx`
- `phase-2-manual_cloud_deployment/requirements*.txt`

to `phase-3-proper-infra/` .

I started the phase by committing the phase 3 folder to the new branch.

### 1.2. Introducing BAPE (Blind Acoustic Parameter Estimator)

*November 7 - 12* 

So far phase 1 and 2 were using a placeholder onnx model, at the start of phase 3 I got access to the project I was planning to deploy in the first place.

My collaborator shared the "BAPE" (Blind Acoustic Parameter Estimation) GitHub repository with me and a .pth-file of his model, which is a serialized file format used to save the state (weights) of a trained model. I will use this to export an onnx model which will be an essential artifact of our cloud deployment.

This part of the project required me to go beyond cloud engineering and tackle ML Ops.

**To Do:**

- link to onnx

- translate to decision_log:
  - investigating an unknown model, 
  - reverse-engineering its data requirements, 
  - writing an export script to convert it to a deployable format, and 
  - integrating it into a web service

**Thoughts before process:**

- The BAPE repository seems solely focussed on model training. #Why?
- What do I need to understand about the repository? What would a professional setting demand? What not?
- What would be my contribution in an ML deployment project? Where do I add value? For developers, executives,…?

My collaborator never deployed the model until now: I asked him 
- how this step would ideally support him, 
- what he would be able to learn from a deployment. 
  
The model produces various information, but the required/ideal output is undefined.
=> explore profiling, logging, graphing and monitoring opportunities

- the repository is set up in .py and .yaml files, I also see that the project uses Hydra which I never heard of
=> a short investigation made me understand that hydra is a configuration app for complex hierarchical projects, it uses yaml files to define (default) configurations for (Python) source code

**Rough plan for BAPE integration:**

1. Code archeology: Make sense of the project repository, find the `__main__` script and retrace it's processes and inputs.
2. Model export: Build an exporter script which builds the architectural shell (provided by the BAPE repository), loads `*.pth` file (model weights) and export the model as an `onnx`.
3. Audio preprocessing: The model takes in Melspectrograms (image graphs, which are always 4d tensors: batch, channels, height, width) as input, we will need to edit `audio_processor.py` to transform audio input into Melspectrograms and adapt the 4d shape.
4. Local testing on local FastAPI-wrapper / run `api.py`: Load model, run inference session, get results. 
5. With the new source code input, new dependencies will likely be introduced. 
`requirements.txt` will need updates/upgrades; important for the projects README
6. Learn about model outputs, improve resulting format and information.
7. *Continue to deploy asap*

### 1.3 Code archaeology: Making sense of the BAPE repository
After receiving the invite to the BAPE repo, I wanted to make myself familiar with the project structure and learn what I would need to change in my existing repo to deploy and run the BAPE model.

I was looking for: 
- the main model, 
- the preprocessing logic for model input and 
- the model's input shape requirements

Scanning the folder structure I learned that a `conf/` folder with `.yaml` files is the structure of a Hydra app, which is

> *an open-source Python framework that simplifies the development of research and other complex applications. The key feature is the ability to dynamically create a hierarchical configuration by composition and override it through config files and the command line. The name Hydra comes from its ability to run multiple similar jobs - much like a Hydra with multiple heads.*

The starting point for my search was the goal to find the main model training script. As Hydra uses `defaults` to define the default elements in complex hierarchical projects, it also defines a default `model`. In `conf/train_speech_encoder.yaml` I found the definition `model: speech_encoder`. 
This lead me to the model specific config file under `conf/model/speech_encoder.yaml`. It defines `_target_: src.model.speech_encoder.SpeechEncoder` and thereby gave me the path of the main (default) model under `src/model/speech_encoder.py`. In that file the `SpeechEncoder` class is defined and from its `forward` function I learned that the model takes one input only, `x: Tensor`:


```speech_encoder.py
# (…)
class SpeechEncoder(nn.Module):
    #(…)
    def forward(
        self, x: Tensor
    ) -> Tuple[Tensor, Tensor, Optional[Tensor], Optiona[Tensor]]:
#    (…)
```

Next, I needed to understand what exact input parameters are required, how the preprocessing pipeline functions.
Scanning the folder structure again, I saw that the project separates `data` and `data_gen` – it's not just loading data but needs to prepare/generate it for inference.

Again, looking at the main model training config, `conf/train_speech_encoder.yaml`, under `defaults:`, the default `data:` definition is `speech`, leading me to `conf/data/speech.yaml`. 
Tracing the `data:` key, I ws looking for specific input parameters like `sample_rate` but found that `speech.yaml` was instead referencing `pyd`-files, which, in the context `webdataset`  are arbitrary file extensions within a `.tar` archive. (The target of `conf/data/speech.yaml` is `DataModule` class, which is defined in the `src/data/datamodule.py` script and imports `webdataset`.) I understand `wetspec.pyd` as "a data blob that contains the wet spectrogram data." So I had to further trace where the pyd file came from.

From there I found `conf/datagen_speech.yaml`, which defines the input parameters for the `generate` function of `src/datagen/speech.py` as well as two complex input objects, `speech_representation`and `rir_representation`, including their `_target_` defined as `src.util.signals.MelSpectogram` and other parameters.
This information helped me understand that the main data input (as configured in `conf/train_speech_encoder.yaml`) are MelSpectograms as defined here.
MelSpectograms are a 2D representaion of audio signals. They are defined by their mel frequency bins, or `n_mels`, defining the spectograms height, here `16`, and their `trunc`, here `2000`, a definition of if and how the input is truncated, defining the width of the spectogram. This gave me the the understanding that the input shape is `[1, 16, 2000]` (batch size, height, width).
But as the the config of the main model, `conf/model/speech_encoder.yaml` configures the parameters for `SpeechEncoder` instances, it defines `front_end`, `sequence_model` and `error_model` as input objects with `cnn2d.CNNEncoder` and `seq.SequenceModel` as target classes. As `cnn2d.CNNEncoder` is a `Conv2d` layer it is designed to work on images, and images are always represented as 4D tensors (Batch, Channels, Height, Width). So for the input of the `generate` function the input tensor would need to have the shape `[1, 1, 16, 2000]` (bacth size is 1, channel is 1 because grayscale image, `n_mels`/height are 16 and the graph is truncated at 2000)

This gave me a rather clear challenge: Write a script that programmatically reconstructs the model's architecture by interpreting the Hydra configuration, loads the weights, and performs the ONNX export.

### 1.4. Model export

And so I retraced the process of training the model in order to understand the preprocessing and the export:

- A user runs the `train_speech_encoder` task. 

- Hydra, the config system loads `conf/train_speech_encoder.yaml`, which defines a default model, `speech_encoder`.
*`exporter.py` will need to import the `SpeechEncoder` class from `speech_encoder`.*

- This default model is configured in `conf/model/speech_encoder.yaml`, it targets the `SpeechEncoder` class of `src/model/speech_encoder` and provides 3 data objects, `frontend` (target is `CNNEncoder` class of `src/model/cnn2d`), `sequence_model`(target is `SequenceModel` class of `src/model/seq`) and `error_model` (target is `SequenceModel` class of `src/model/seq`).
*In order to rebuild the architecural shell of the `speech_encoder` model, `exporter.py` will need to import these dependencies (`cnn2d.py`, `seq.py`), , so we can instantiate their classes.*

- With the architectural shell in place, `exporter.py` must now imitate the data preprocessing logic of the `speech_encoder` model. Again the `train_speech_encoder.yaml` tells us that `speech` is the default data, so we look for further information in `conf/data/speech.yaml`. There I expected clear cut input parameters but instead found `pyd` files referenced as data input, meaning preprocessed data. So the model not just loads raw data, it preprocesses/generates it. 
- The data config `conf/data/speech.yaml` names a `DataModule` class instance as its target, and, tells us that it consumes data from urls where it expects `.pyd` files. These must be created and we find their recipes in `conf/datagen_speech.yaml`: 
This config file targets the `generate` function of `src/datagen/speech` and, besides clear parameters, provides config values for `speech_representation`, an instance of the `MelSpectogram` class, and another `MelSpectogram` instance called `rir_representation`, with its own config values.
*`exporter.py` must do the same and instantiate `MelSpectogram` as a preprocessor for data input. It also must generate a dummy audio signal. This will have the shape of (64000,) (4 sec * 16000 samples/sec)*
- *`exporter.py` then forwards the dummy input through the preprocessor which forms it to a Tensor of the shape `[16, 2000]` (height, width)*
*Next, it adds a bacth size dimension to the tensor at the first position (`.unsqueeze(0)`) giving the tensor a shape of `(1, 16, 2000)` (batch size, height, width)*
*As the CNNEncoder class is a Conv2d layer (`torch.nn.Conv2d()`) it expects 4 arguments (bacth size, channels, height width), so `exporter.py` must unsqueeze the tensor at position 1.*

- This finishes the preprocessing of the input: we have the architectural shell, the preprocessed dummy input and can now load the pth weights.

- `exporter.py` uses `torch.load()` to load the pth from path into a dictionary named `state_dict`.

- Next it uses the `load_state_dict()` function of the `SpeechEncoder`instance `model`to load the dictionary*

At this point the script was failing. The Traceback reported there are errors in loading `state_dict` for `SpeechEncoder` and was listing missing keys. At first glance one could see that almost all keys loaded in `state_dict` were beginning with `encoder.`. Those reported as missing had the same names without the starting `encoder.`

`exporter.py` was updated with additional instructions to 
- order the dict (`new_state_dict`)
- run through all entries, and if a key starts with the `encoder.` prefix
    - the key is redefined as the key minus the starting prefix

- `exporter.py` uses `model.load_state_dict(new_state_dict, strict= False) to load again. This time successfully.

After setting the model to evaluation mode, we instruct the ONNX export:

In the [`torch.onnx.export` documentation](https://docs.pytorch.org/docs/stable/onnx_export.html#torch.onnx.export) we find the required parameters for the export and we specify our export:
- we define model as `model`, our instance of `SpeechEncoder`
- give example positional inputs from the preprocessed `final_4d_tensor``
- defin the path, where to export the model
- we give more descriptive input and output names
- we define dynamic axes to enable dynamic batch sizes, so one or more input files


Running the `exporter.py` I had several issues. I learned about the shape requirements of Conv2d layers and when the onnx.export returned a TimeoutError immediately, I learned that my Python 3.13 version was too new and not yet supported by the torch library. So I saved my virtual environment closed and stored it, to create a new one with the more robust Python3.11 

---

### 1.5. Refactoring `audio_processor.py` to support the new model.

The onnx model we just exported expects a MelSpectogram input with a shape of `(1, 1, 16, 2000)`.
I have to update the `audio_processor.py` to support this requirement.

Copied `MelSpectrogram` class from `BAPE/src/util/signals.py`.
Instantiated it with config values from `conf/datagen_speech`'s `speech_representation` object.

### 1.6. Local testing on local FastAPI-wrapper / run `api.py`: Load model, run inference session, get results. 

TBD

### 1.7. Learn about model outputs, improve resulting format and information.

TBD

### 1.8. Cleanup for cloud deployment / requirements,… 
`requirements.txt` will need updates/upgrades; important for the projects README
Decided to use `pipreqs`. Had to weed out training and model export dependencies, like `hydra-core`, `datasets`or `lightning`.

### 1.9. Later edits
As I did not yet profile the memory usage of the `generate_vector()` function I installed the `memory_profiler` package and added `from memory_profiler import memory_usage` to profile the memory usage of the `generate_vector` function we run to get our results.

[2025-11-18] I learned that the speech encoder only produces a necessary input for the main model, ParameterEstimator.
As my friend only benefits from the final results of the ParameterEstimator, I refactored my code right away, but made a small addition: The ParameterEstimator returns outputs (estimated_params) and quantiles_adjusted but I wanted to make the SpeechEncoder results, the acoustic finger print, visible as well to deliver a more complete response. So, I created a new class (`SuperParameterEstimator`)in the updated exporter script which is very much the same as the `ParameterEstimator` but also returns `z`, the latent vector resulting from the speech encoder, as `latent_vector`.
I later on learned that the bape project does not only use an CNNEncoder model to encode speech but there is also a CNNDecoder which should be able to decode speech from `latent_vector`, the output of the speech encoder and input to the parameter estimator.

Refactoredto new files:
- `exporter.py` -> `param_estimator-onnx_exporter.py` (defines `SuperParameterEstimator` class, which takes in an `ParameterEstimator` instance and returns both the results of the SpeechEncoder and the ParameterEstimator. 
When this new `SuperParameterEstimator` architecture is built, instantiating all required models, it loads an updated pth file my friend also gave me to load into this arch, resulting in an instance called `param_estimator_model`. 
Then, just as before, a dummy audio tensor is generated and formated for model input which happens during the final `torch.onnx.export`, which also defines the three returning values `z, outputs and quantiles_adjusted` as `latent_vector`, `estimated_params` and `quantiles`. The export produces `super_param_estimator.onnx`)

- `api.py` was not renamed but updated to use the new `super_param_estimator.onnx` model, also the API response was updated for the new results

## 2. Actual cloud deployment.

### 2.1. Drafting of required resources

I set out to define what resources would be required:

- 1 VPC

- 1 IGW

- 4 Subnets in two AZs
    - 2 public for 2 NATGWs, 
    - 2 private for EC2 instances
    -> 1 private + 1 public per AZ

    *initially was*
    - 2 Subnets
        - 1 public for NAT Gateway
        - 1 private for EC2 instances
        - 2 RTs (1 per subnet)

As I was using Gemini to suggest an incremental learning path forward, it suggested deploying two ALB nodes in two public subnets in different AZs and in one of these AZs also a private subnet containing the EC2 instance.
After pushing several times against the idea of having only one target for the two ALB nodes (as described further up), the model was still sure about this increment making sense. To experience what is working and what is not I complied, and went for

- 3 Subnets in 2 AZs
    - 1 public subnet in each AZ, each containing a NATGW
    - 1 private subnet in one of the AZs
    - in each AZ there is an ALB node

- ELB / ALB
    - 1 ALB node in each AZ

- S3 bucket storing model
    - api.py calls onnx-model
    - IAM Role/ instance profile for instance accessing S3

### 2.2. CIDR-planning / IP-Ranges to avoid (TBD!)

- max CIDR is 10.0.0.0/16
- common ranges to avoid
    - 10.1.0.0/?
        10.1.0.0 – 10.15.0.0
    - 10.0.0.0/8:
        10.0.0.0 – 10.0.0.255
    - 169.254.0.0/16:
        169.254.0.0 – 169.254.255.255
    - 172.16.0.0/12
        172.16.0.0 - 172.32.255.255

#### First Proposal
- VPC CIDR: 10.16.0.0/16
    - Public Subnet 10.16.0.0/17: 10.16.0.0 – 10.16.127.255
    - Private Subnet 10.16.127.0/17: 10.16.128.255 - 10.16.255.255

This decision would be fine per se, but both subnets would have 32768 IP addresses, half of all addresses available, which makes future additions complicated or impossible.
Changing from /17 subnets to /24 subnet CIDR ranges, gives each subnet 256 addresses out of a 65,536 VPC CIDR range and seems much more reasonable so the decision was 
revised to:

- VPC CIDR: 10.16.0.0/16
    - Public Subnet 10.16.0.0/24: 10.16.0.0 – 10.16.0.255
    - Private Subnet 10.16.1.0/24: 10.16.1.0 - 10.16.1.255

As the amount of subnets is subject to change, it should be mentioned that this is most importantly about switiching from /17 ranges to /24 ranges.

Furthermore I sketched out first architecture diagrams in draw.io:

### 2.3. Architecture TBD!!

draw-io / Architecture images (placeholders) or mermaid?

---

![2AZx4SN-ALB+2NATGW+2EC2] ("Image-URL")
Moving too fast: I was immediately trying to build a resilient and highly available infra which will be necessary for production, but I'll iterate in smaller steps to get there.

---

[1AZx2SN-ALB+NATGW+2EC2] ("Image-URL")
Good practice but let's build this up step by step…

---

![1AZx2SN-ALB+NATGW+EC2]("arch/1AZx2SN-ALB+EC2.drawio.png")

…, seems good now. But… 

With an Application Load Balancer however, it is a requirement that you enable at least two or more Availability Zones. This configuration helps ensure that the load balancer can continue to route traffic. If one Availability Zone becomes unavailable or has no healthy targets, the load balancer can route traffic to the healthy targets in another Availability Zone.
*From* [How Elastic Load Balancing works – Availability Zones and load balancer nodes](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/how-elastic-load-balancing-works.html#availability-zones)

During the setup of the resource definitions I became more and more familiar with the resource requirements and it didn't take long to realize, I would need to create 
- a NAT Gateway in a public subnet and 
- an EC2 instance in a private subnet and 
- an ALB node in their common AZ.

This I would need to create twice in two distinct AZs for high availability and for the ALB nodes to have sufficient targets.

![Current setup]("../../phase-3-proper-infra/docs/260113_2AZx2ALBx1EC2_vpc.drawio.svg")


---
#### ***HOW DOES THIS FIT IN???***
***What is correct/wrong?***

```mermaid
graph TB
    Internet([Internet Traffic])
    
    subgraph VPC["🔷 VPC - 10.0.0.0/16"]
        IGW[🌐 Internet Gateway]
        subgraph Public["📡 Public Subnet - AZ1 (10.0.1.0/24)"]
            ALB[⚖️ Application Load Balancer<br/>HTTP/HTTPS]
            NAT[🔀 NAT Gateway<br/>Elastic IP]
        end
        
        subgraph Private1["🔒 Private Subnet 1 - AZ1 (10.0.10.0/24)"]
            EC2_1[💻 EC2 Instance 1<br/>t3.medium<br/>App Server]
        end
        
        subgraph Private2["🔒 Private Subnet 2 - AZ2 (10.0.20.0/24)"]
            EC2_2[💻 EC2 Instance 2<br/>t3.medium<br/>App Server]
        end
        
        RT_Public[📋 Route Table: Public<br/>0.0.0.0/0 → IGW]
        RT_Private[📋 Route Table: Private<br/>0.0.0.0/0 → NAT]
    end
    
    %% Inbound Traffic Flow
    Internet -->|HTTPS:443| IGW
    IGW --> ALB
    ALB -->|Health Check<br/>Load Balance| EC2_1
    ALB -->|Health Check<br/>Load Balance| EC2_2
    
    %% Outbound Traffic Flow
    EC2_1 -.->|Outbound<br/>apt update, etc.| NAT
    EC2_2 -.->|Outbound<br/>apt update, etc.| NAT
    NAT -.-> IGW
    
    %% Route Table Associations
    RT_Public -.->|Associated| Public
    RT_Private -.->|Associated| Private1
    RT_Private -.->|Associated| Private2
    
    %% Styling
    classDef publicStyle fill:#ff9900,stroke:#232f3e,stroke-width:2px,color:#fff
    classDef privateStyle fill:#3b48cc,stroke:#232f3e,stroke-width:2px,color:#fff
    classDef trafficStyle fill:#27ae60,stroke:#232f3e,stroke-width:2px,color:#fff
    
    class ALB,NAT,IGW publicStyle
    class EC2_1,EC2_2 privateStyle
    class Internet trafficStyle
```
---

This built the foundation for the cloud deployment described in the next chapter


The resulting resources were documented and described iteratively in the last chapter *X. Resources*. Iteratively because as resources were built IDs/identifiers became available for subsequent commands.
Also, resources causing costs were tore down at the end of sessions and rebuilt when I returned. Having the resources and their information properly documented was essential to keep pace. Nevertheless, it caused me a lot of work and it motivated me enormously to keep pushing in order to benefit from the automation of Infrastructure as Code, which is used in phase 4.

### 2.4. Cloud deployment via AWS CLI

First tries to define the VPC.

#### Log in via SSO Identity Center:

```zsh
aws sso login --profile dev
```

#### 2.4.1. Create resources

##### 2.4.1.1. VPC

```zsh
aws ec2 create-vpc \
--cidr-block 10.16.0.0/16 \
--tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=phase3-vpc}]" \
--profile "dev" \
--region "eu-central-1"
```
-> retrieve VPC-ID

##### 2.4.1.2 .Subnets

```zsh
aws ec2 create-subnet \
--cidr-block 10.16.0.0/24 \
--tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=phase3-public-subnet-a}]" \
--vpc-id # retrieve from 'X. Resources'\ 
--profile "dev" \
--region "eu-central-1" \
--availability-zone "eu-central-1a"

aws ec2 create-subnet \
--cidr-block 10.16.1.0/24 \
--tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=phase3-public-subnet-b}]" \
--vpc-id # retrieve from 'X. Resources'\ 
--profile "dev" \
--region "eu-central-1" \
--availability-zone "eu-central-1b"

aws ec2 create-subnet \
--cidr-block 10.16.2.0/24 \
--tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=phase3-private-subnet-a}]" \
--vpc-id # retrieve from 'X. Resources'\ 
--profile "dev" \
--region "eu-central-1"
--availability-zone "eu-central-1c"
```
After subnet creation I was able to retrieve the Subnet-IDs; documented in *X. Resources*

##### 2.4.1.3. Internet Gateway

```zsh
aws ec2 create-internet-gateway \
--tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=phase3-igw}]" \
--profile "dev" \
--region "eu-central-1"
```
After internet gateway creation I was able to retrieve the IGW-ID; documented in *X. Resources* 

###### Attaching the IGW to the VPC:
```zsh
aws ec2 attach-internet-gateway \
--internet-gateway-id # retrieve from 'X. Resources'\
--vpc-id # retrieve from 'X. Resources'\
--profile "dev" \
--region "eu-central-1"
```
With the VPC connected to the IGW / public internet, I was able to define route tables and thereby make traffic possible,

##### Public and private route tables
```zsh
aws ec2 create-route-table \
--tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=phase3-public-route-table}]" \
--vpc-id # retrieve from 'X. Resources'\
--profile "dev" \
--region "eu-central-1"

aws ec2 create-route-table \
--tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=phase3-private-route-able}]" \
--vpc-id # retrieve from 'X. Resources'\
--profile "dev" \
--region "eu-central-1"
```
##### Set up PUBLIC networking
Create public route table first so that route table ID can be retrieved to create routes.

```zsh
aws ec2 create-route \
--route-table-id # retrieve from 'X. Resources'\
--destination-cidr-block 0.0.0.0/0
--gateway-id # retrieve from 'X. Resources'\
--profile "dev" \
--region "eu-central-1"
```
associate public route table to public subnets

```zsh
aws ec2 associate-route-table \
--route-table-id # retrieve from 'X. Resources'\
--subnet-id # retrieve from 'X. Resources'\
--profile "dev" \
--region "eu-central-1"

aws ec2 associate-route-table \
--route-table-id # retrieve from 'X. Resources'\
--subnet-id # retrieve from 'X. Resources'\
--profile "dev" \
--region "eu-central-1"
```
– PUBLIC NETWORKING COMPLETE –

##### Set up PRIVATE networking

```zsh
aws ec2 associate-route-table \
--route-table-id # retrieve from 'X. Resources'\
--subnet-id # retrieve from 'X. Resources'\
--profile "dev" \
--region "eu-central-1"
```

#### Change of requirements

At this point the requiremnts for the app changed and were updated:

- real-time input via mic and real-time output of results as graph
- no microphone signal via the public internet
- find ways to make model access efficient
  - download model with mobile app?
  - download model into browser cache?

ONNX provides a *web* functionality allowing the browser to run input against the model without sending any user input or other data via the public internet. 
The possibility of our app leaking microphone signals of interested users would not be acceptable, and the privacy of the users must be guaranteed at any time.

#### …Resource Creation continued…


```zsh
##### Allocating elastic IP
aws ec2 allocate-address \
--domain vpc \
--tag-specifications "ResourceType=elastic-ip, Tags=[{Key=Name,Value=phase3-eip}]" \
--profile "dev" # \
# --region "eu-central-1" already defined in profile

##### Creating the NAT-Gateway
aws ec2 create-nat-gateway \
--subnet-id # retrieve from 'X. Resources' / Public Subnet A\
--allocation-id # retrieve from 'X. Resources' / phase3-eip \
--tag-specifications "ResourceType=natgateway,Tags=[{Key=Name,Value=phase3-natgw}]" \
--profile "dev"
```

Tell the private route table to send all traffic to the NAT Gateway
```zsh
aws ec2 create-route \
--route-table-id # retrieve from 'X. Resources' / phase3-private-table \
--destination-cidr-block 0.0.0.0/0 \
--gateway-id # retrieve from 'X. Resources' / phase3-natgw \
--profile dev
```

Now, the outbound engine is live and I need a place to store the model (`super_param_estimator.onnx`) and the BAPE submodule(?) in the cloud. From there, the EC2 instance will fetch them during boot.

##### Create an S3 bucket for storage

```zsh
aws s3 mb s3://onnx-deployment-phase3-artifacts-dgoossens-20250106 \
--profile dev
```

#### Prepare Artifacts

##### zip the BAPE submodule locally

```zsh
#from /phase-3-proper-infra
zip -r bape_src.zip src/BAPE_src
```

##### upload the onnx module and the zipped submodule to the S3 bucket
```zsh
aws s3 cp onnx/super_param_estimator.onnx \
s3://onnx-deployment-phase3-artifacts-dgoossens-20250106 \
--profile dev

aws s3 cp bape_src.zip \
s3://onnx-deployment-phase3-artifacts-dgoossens-20250106 \
--profile dev
```

#### Roles, Policies and Permissions

1. creating `trust-policy.json` to grant EC2 permission to assume the IAM role
2. creating `s3-access-policy.json` to grant the IAM role permission to `s3:GetObject` from the bucket

Once the policies are created, we can create the role,…

##### Creating the IAM role for the EC2 instance to download the model (and log in via AWS Systems Manager)

```zsh
aws iam create-role \
--role-name phase3-ec2-role \
--assume-role-policy-document file://trust-policy.json \ 
#given the terminal is currently in the containing folder
--profile dev
```

##### …attach the S3 permissions and…

```zsh
aws iam put-role-policy \
--role-name phase3-ec2-role \
--policy-name phase3-s3-access \
--policy-document file://s3-access-policy.json \
--profile dev
```

##### …attach the Systems Manager (SSM) permissions.
```zsh
aws iam attach-role-policy \
--role-name phase3-ec2-role \
--policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore \
--profile dev
```

##### Create the Instance Profile 
The instance profile is the instance wrapper actually carrying the IAM role…

```zsh
aws iam create-instance-profile \
--instance-profile-name phase3-ec2-profile \
--profile dev
```

##### …and attach the role:
```zsh
aws iam add-role-to-instance-profile \
--instance-profile-name phase3-ec2-profile \
--role-name phase3-ec2-role \
--profile dev
```

#### Uploading artifacts

##### upload api.py and requirements.txt to S3

Before uploading the requirements.txt I need to make sure it's production-ready and not bloated.

From the result of `pip freeze > requirenments.txt` I curated a list of my top-level imports, called `requirements.in`:

```Text
# Core API
fastapi==0.127.1
uvicorn==0.40.0
python-multipart==0.0.21

# ML Runtime
onnxruntime==1.23.2
numpy==1.26.4

# Audio Processing
librosa==0.11.0
soundfile==0.13.1

# Utils (Used by BAPE)
pyyaml
coloredlogs==15.0.1
humanfriendly==10.0
```

and compiled it with `pip-compile requirements.in`.

upload `requirements-prod.txt` as `requirements.txt` to S3 :

```zsh
aws s3 cp requirements-prod.txt s3://onnx-deployment-phase3-artifacts-dgoossens-20250106/requirements.txt --profile dev
```

Upload api.py to S3:
```zsh
aws s3 cp api.py s3://onnx-deployment-phase3-artifacts-dgoossens-20250106/api.py --profile dev
```

#### create user_data.sh [LINK].

#### Launch EC2 instances

We want to start an AL2023 instance in `eu-central-1`.

We can find the AMI ID in the AWS console or search for it via the CLI:

```zsh
aws ec2 describe-images --owners amazon --filters "Name=name,Values=al2023-ami*-x86_64" --query "sort_by(Images, &CreationDate)[-1].ImageId" --output text --profile dev
```

-> gives us `ami-029cdb80a7069a70a`

Now we can build the launch command:

```zsh
aws ec2 run-instances \
--image-id ami-029cdb80a7069a70a \
--instance-type t3.small \
--subnet-id subnet-0f8b792c550dc1f57 \
--security-group-ids #incmoplete! \
--profile
```

##### Security Groups required!

…not yet. The security groups are still missing, I need to create them to have their ids for the launch command:

```zsh

# Create SG for ALB

aws ec2 create-security-group \
--group-name phase3-sg-alb \
--description "ALB Security Group" \
--vpc-id # retrieve from 'X. Resources' \
--tag-specifications 'ResourceType=security-group,Tags=[{Key=Name,Value=phase3-sg-alb}]' \
--profile dev

# Create SG for EC2

aws ec2 create-security-group \
--group-name phase3-sg-ec2 \
--description "EC2 Security Group" \
--vpc-id # retrieve from 'X. Resources' \
--tag-specifications 'ResourceType=security-group,Tags=[{Key=Name,Value=phase3-sg-ec2}]' \
--profile dev
```


##### Interruption: Tear-Down and Rebuild of non-free infra

I had to take a break here which made me experience an essential benefit of IaC: the instant termination and restart of resources.

The following steps would have been two clicks with infrastructure as code:

1. Tearing down non-free resources
```zsh
#tearing down the resources using up my AWS org's budget, 

#NAT gateway… 
aws ec2 delete-nat-gateway \
--nat-gateway-id nat-01… \
--profile dev

#…and elastic IP
aws ec2 release-address \
--allocation-id eipalloc-01… \
--profile dev
```

2. Restore non-free resources (as in *Creating the NAT-Gateway*)
```zsh
#allocate Elastic IP
aws ec2 allocate-address \
--domain vpc \
--tag-specifications "ResourceType=elastic-ip, Tags=[{Key=Name,Value=phase3-eip}]" \
--profile "dev"

#create NATGW in public subnet A
aws ec2 create-nat-gateway \
--subnet-id subnet-… # retrieve from 'X.1.1. Resources › VPC › Subnets' / Public Subnet A \
--allocation-id # retrieve from 'X.7. Resources › Elastic IP' \
--tag-specifications "ResourceType=natgateway,Tags=[{Key=Name,Value=phase3-natgw}]" \
--profile "dev"
```

3. Replace outdated private Route

I already have a private route directing all outbound traffic (`--destination-cidr-block 0.0.0.0/0`) to the NATGW, but it still has the Gateway ID of the old NATGW. 
I also have a public route directing all traffic to the IGW but since these are free resources, I didn`t change them and so we only need to replace the NATGW ID for the recreated NATGW.

```zsh
aws ec2 replace-route \
--route-table-id # retrieve from 'X.6. Route Tables` \
--destination-cidr-block 0.0.0.0/0 \
--nat-gateway-id # retrieve from 'X.3. NATGW` \
--profile dev
```

##### Back to defining the security groups: Opening the firewalls

I created the security groups already but they are empty for now. I must allow traffic:

Allow ingress traffic from anywhere to ALB via TCP on port 80 and 443:

```zsh
aws ec2 authorize-security-group-ingress \
--group-id #retrieve from 'X.5.1. ALB Security Group' \ sg-040e0a1163cf1f846 \
--protocol tcp \
--port 80 \
--cidr 0.0.0.0/0 \
--profile dev

aws ec2 authorize-security-group-ingress \
--group-id #retrieve from 'X.5.1. ALB Security Group' \ sg-040e0a1163cf1f846 \
--protocol tcp \
--port 443 \
--cidr 0.0.0.0/0 \
--profile dev
```

Allow ingress traffic to the EC2 instance via TCP on port 8000, ONLY FROM the ALB:
```zsh
aws ec2 authorize-security-group-ingress \
--group-id #retrieve from 'X.5.2. EC2 Security Group' \ sg-0eefa1fcc6557d2f8 \
--protocol tcp \
--port 8000 \
--source-group #retrieve from 'X.5.1. ALB Security Group' \ sg-040e0a1163cf1f846 \
--profile dev
```
I created the security groups as they were required for launching the EC2 instance (See"Launch EC2 instances").

##### Launching the instance

Now, I should be able to complete the launch command:

```zsh
aws ec2 run-instances \
# ami-id retrieved via 'ec2 describe-images…'
--image-id ami-029cdb80a7069a70a \
--instance-type t3.small \
#private subnet
--subnet-id subnet-0f8b792c550dc1f57 \
--security-group-ids sg-0eefa1fcc6557d2f8 # retrieved from 'X.5.2. EC2 Security Group' \
--iam-instance-profile Name=phase3-ec2-profile \
--user-data file://user_data.sh \
--tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=phase3-inference-node}]' \
--profile dev
```

After 2 minutes, I ran

```zsh
aws ec2 describe-instances --profile dev
```
to get the instance ID.

##### Connect to SSM

With this I tried to connect to SSM without SSH

```zsh
aws ssm start-session --target i-04aaa7bc345a24671 --profile dev
```

but FAILED with a `TargetNotConnected`.

##### Troubleshooting SSM Access

EC2 instance in the private subnet A doesn't connect to the NATGW in the public subnet A. so I checked if the route tables are connected correctly:

###### Check Routes

```zsh
aws ec2 describe-route-tables \
    --filters "Name=vpc-id,Values=vpc-0772e7cc248fd716c" \
    --query "RouteTables[*].{ID:RouteTableId,Name:Tags[?Key=='Name']|[0].Value,Routes:Routes}" \
    --profile dev
```

This will return the Route tables in my VPC with 3 main pieces of information: ID, Name and and Routes.

In this case it returns 
```JSON
{
        "ID": "rtb-08d988d32de122e1c",
        "Name": null,
        "Routes": [
            {
                "DestinationCidrBlock": "10.16.0.0/16",
                "GatewayId": "local",
                "Origin": "CreateRouteTable",
                "State": "active"
            }
        ]
    },
    {
        "ID": "rtb-00dcbd16b07bf8e46",
        "Name": "phase3-public-route-table",
        "Routes": [
            {
                "DestinationCidrBlock": "10.16.0.0/16",
                "GatewayId": "local",
                "Origin": "CreateRouteTable",
                "State": "active"
            },
            {
                "DestinationCidrBlock": "0.0.0.0/0",
                "GatewayId": "igw-0ca97ba8edc60bcf4",
                "Origin": "CreateRoute",
                "State": "active"
            }
        ]
    }
```

So the first route table has no name and only a local route. This should have been our private route table but instead it defaulted to the "Main" route table > The EC2 instance is sitting in a room without a door.

I force the private route table to link with the private subnet A:

```zsh
aws ec2 associate-route-table \
--subnet-id subnet-0f8b792c550dc1f57 \
--route-table-id rtb-0d180e4bfff0d77ee \
--profile dev
```

To update routing I need to restart the instance:

```zsh
aws ec2 reboot-instances \
--instance-ids i-04aaa7bc345a24671 \
--profile dev
```

Another try:
```zsh
aws ssm start-session --target i-04aaa7bc345a24671 --profile dev
```
But again, I was returned a `TargetNotConnected`.

I checked `describe route-tables` again to make sure this wasn`t the cause again and it looked fine:
```zsh
onnx-acoustic/phase-3-proper-infra on  feat/proper-AWS-deployment [$✘!?] via 🐍 v3.13.7 (m4-mini) 
❯ aws ec2 describe-route-tables \
--filters "Name=vpc-id,Values=vpc-0772e7cc248fd716c" \
--query "RouteTables[*].{ID:RouteTableId,Name:Tags[?Key=='Name']|[0].Value,Routes:Routes}" \
--profile dev
[
    {
        "ID": "rtb-0d180e4bfff0d77ee",
        "Name": "phase3-private-route-able",
        "Routes": [
            {
                "DestinationCidrBlock": "10.16.0.0/16",
                "GatewayId": "local",
                "Origin": "CreateRouteTable",
                "State": "active"
            },
            {
                "DestinationCidrBlock": "0.0.0.0/0",
                "NatGatewayId": "nat-095f0051a71bbe536",
                "Origin": "CreateRoute",
                "State": "active"
            }
        ]
    },
    {
        "ID": "rtb-08d988d32de122e1c",
        "Name": null,
        "Routes": [
            {
                "DestinationCidrBlock": "10.16.0.0/16",
                "GatewayId": "local",
                "Origin": "CreateRouteTable",
                "State": "active"
            }
        ]
    },
    {
        "ID": "rtb-00dcbd16b07bf8e46",
        "Name": "phase3-public-route-table",
        "Routes": [
            {
                "DestinationCidrBlock": "10.16.0.0/16",
                "GatewayId": "local",
                "Origin": "CreateRouteTable",
                "State": "active"
            },
            {
                "DestinationCidrBlock": "0.0.0.0/0",
                "GatewayId": "igw-0ca97ba8edc60bcf4",
                "Origin": "CreateRoute",
                "State": "active"
            }
        ]
    }
]
```

##### Check SGs

Next, I checked if the egress rules of the security group could be the cause but it wasn't:

```zsh
aws ec2 describe-security-groups \
    --filters Name=group-name,Values=phase3-sg-ec2 \
    --query "SecurityGroups[*].IpPermissionsEgress" \
    --profile dev
[
    [
        {
            "IpProtocol": "-1",
            "UserIdGroupPairs": [],
            "IpRanges": [
                {
                    "CidrIp": "0.0.0.0/0"
                }
            ],
            "Ipv6Ranges": [],
            "PrefixListIds": []
        }
    ]
]
```
With our query filtering out our specific EC2 security group, only looking at egress permissions, `"IpProtocol": "-1"` tells us that it allows all protocols and `"CidrIp": "0.0.0.0/0"` that it allows all destinations. This looks fine.

***Pause >> ShutDown: Terminate Instance, delete NAT Gateway, release Elastic IP***

##### Check DNS settings

For the trouble shooting to continue it was not necessary to immediately restart the non-free resources. Instead I wanted to check basic networking settings.

*Does the IAM Role have access to the SSM?*

Checking Role Permissions for `AmazonSSMManagedInstanceCore` policy:

`aws iam list-attached-role-policies --role-name phase3-ec2-role --profile dev`

returns

```JSON
{
    "AttachedPolicies": [
        {
            "PolicyName": "AmazonSSMManagedInstanceCore",
            "PolicyArn": "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
        }
    ]
}
```
Check.

*Is DNS support enabled for the VPC?*

```zsh
aws ec2 describe-vpc-attribute --vpc-id vpc-0772e7cc248fd716c --attribute enableDnsSupport --profile dev
```
returns
```JSON
{
    "EnableDnsSupport": {
        "Value": true
    },
    "VpcId": "vpc-0772e7cc248fd716c"
}
```
Check.

*Are Hostnames enabled for the VPC?*

`aws ec2 describe-vpc-attribute --vpc-id vpc-0772e7cc248fd716c --attribute enableDnsHostnames --profile dev`

returns

```JSON
{
    "EnableDnsHostnames": {
        "Value": false
    },
    "VpcId": "vpc-0772e7cc248fd716c"
}
```
This seems to cause the problem.
Without `EnableDnsHostnames` set to true, the EC2 instance gets an IP address but no public DNS hostname.

*Enabling DNS Hostnames*

```zsh
aws ec2 modify-vpc-attribute \
--enable-dns-hostnames "{\"Value\":true}" \
--vpc-id vpc-0772e7cc248fd716c \
--profile dev
```

Check attribute:
```zsh
aws ec2 describe-vpc-attribute --vpc-id vpc-0772e7cc248fd716c --attribute enableDnsHostnames --profile dev
```

```JSON
{
    "EnableDnsHostnames": {
        "Value": true
    },
    "VpcId": "vpc-0772e7cc248fd716c"
}
```

Troubleshooting can be finished after retrying with non-free infrastructure relaunched.

##### Restarting infra

- Allocate IP (see #### …resource Creation continued…):
`aws ec2 allocate-address…`

- Create NAT GW with EIP:
`aws ec2 create-nat-gateway`

- replace exisiting route in private route table (routes to the old IP of the old NATGW):

launch instance

---
At this stage, my remote repository needed an update because I was refatoring the bigger project structure and wanted to update my logs (todo: add commit!).

With the updates in place I wanted to make sure my code is at the latest version:

```zsh
#from the `phase-3-proper-infra` directory:
aws s3 cp api.py s3://onnx-deployment-phase3-artifacts-dgoossens-20250106/api.py --profile dev
aws s3 cp requirements.txt s3://onnx-deployment-phase3-artifacts-dgoossens-20250106/requirements.txt --profile dev
```

Retrying to establish SSM connection failed again.
Since I manually wrote the user-data.sh script, I decided to launch a plain vanilla ec2 t3.small instance without a user data script and try to establish a connection.

Retrying `aws ssm start-session …` failed again.

I decided to cancel out the causes and launch an instance into one of the public subnets. If this works, we know the problem is with the private subnet, its route table and the NAT-Gateway. If it fails my problem must stem from the IAM role or the VPC itself (although I checked DNS settings).

Terminate the instance in the private subnet:

`aws ec2 terminate-instances --instance-ids…`

Launch a debug instance in Public Subnet A with an explicit request for a public IP:

```zsh
aws ec2 run-instances \
    --image-id ami-029cdb80a7069a70a \
    --instance-type t3.small \
    # public subnet A
    --subnet-id subnet-0e9fc06ce108ce4ea \
    # EC2 SG
    --security-group-ids sg-0eefa1fcc6557d2f8 \
    --iam-instance-profile Name=phase3-ec2-profile \
    #give the instance a public IP
    --associate-public-ip-address \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=phase3-public-debug}]' \
    --profile dev
```

Also returns the Image ID `i-07cbf883226beb48a`.

Retry to start an SSM Session on this instance:

`aws ssm start-session --target i-…` again returns `TargetNotConnected`.

So the problem must be caused by faulty authentication.
`aws iam get-role` showed the correct allowed access for EC2
`aws get-instance-profile …` showed the role is correctly attached to the instance profile

Also the Route Tables have the correct routes, there are no custom NACLs denying any of the traffic and the IGW is correctly attached to the VPC.

##### Debug Shell Script `debug_ssm.sh` on the EC2 instance

I want to see into the logs of the EC2 instance and 
- create a script to 
- restart the ssm-agent on the instance
- dump the logs into the system console

See `debug_ssm.sh`.

##### Relaunch debug instance with debug script

```zsh
aws ec2 run-instances \                                                              
    --image-id ami-029cdb80a7069a70a \
    --instance-type t3.small \
    --subnet-id subnet-0e9fc06ce108ce4ea \
    --security-group-ids sg-0eefa1fcc6557d2f8 \
    --iam-instance-profile Name=phase3-ec2-profile \
    --associate-public-ip-address \
    --user-data file://debug_ssm.sh \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=phase3-public-debug-script}]' \
    --profile dev
```

Return includes instance ID: `i-03c88e33d895e1659`.

I'm waiting a couple of minutes for the instance to boot, restart SSM Agent, fail at it and print logs.

```zsh
aws ec2 get-console-output --instance-id i-03c88e33d895e1659 --profile dev --output text
```

This try didn't return any SMM logs at all, so I ran another debug script, debug_ssm_2.sh, which
- tries to establish an internet connection via curl
- checks SSM status
- get the 50 last lines of logs from SSM

The connection worked as planned but the status returned `Unit amazon-ssm-agent.service could not be found.`, so SSM didn't seem to be preinstalled as assumed.

##### FIX: install amazon-ssm-agent on EC2 instance and Plugin locally
I corrected my original `user-data.sh` script to `dnf install amazon-ssm-agent`, `systemctl enable` and `start`.

Then I relaunched the instance.

Trying to satrt the ssm session now offered another piece of infomration:

```zsh
aws ssm start-session --target i-03c2bba49961b3e6f --profile dev

SessionManagerPlugin is not found. Please refer to SessionManager Documentation here: http://docs.aws.amazon.com/console/systems-manager/session-manager-plugin-not-found
```

So I needed to download the SSM plugin installer on my machine
```zsh
onnx-acoustic on  feat/proper-AWS-deployment [$!?] 
❯ curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/mac_arm64/session-manager-plugin.pkg" -o "session-manager-plugin.pkg"
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100 3773k  100 3773k    0     0  2023k      0  0:00:01  0:00:01 --:--:-- 2023k

onnx-acoustic on  feat/proper-AWS-deployment [$!?] 
❯ sudo installer -pkg session-manager-plugin.pkg -target /
sudo ln -s /usr/local/sessionmanagerplugin/bin/session-manager-plugin /usr/local/bin/session-manager-plugin
Password:
installer: Package name is session-manager-plugin
installer: Installing at base path /
installer: The install was successful.

onnx-acoustic on  feat/proper-AWS-deployment [$!?] took 7s 
❯ aws ssm start-session --target i-03c2bba49961b3e6f --profile dev                                                                            

Starting session with SessionId: admin2026-advjkuyike5p9qghg8c9tv4ir4


SessionId: admin2026-advjkuyike5p9qghg8c9tv4ir4 : Plugin with name Standard_Stream not found. Step name: Standard_Stream
```

##### Adjusting the instance for boot success

So, the session starts but doesn't establish.
I wanted to see what the instance is logging during boot:
```zsh
aws ec2 get-console-output \
--instance-id i-… \
--profile dev \
--output text
```
And learned that the disk might be full:
```zsh
[   62.955228] cloud-init[1939]: src/BAPE_src/results.tgz:  write error (disk full?).  Continue? (y/n/^C)
[   62.955332] cloud-init[1939]: warning:  src/BAPE_src/results.tgz is probably truncated
```

- the `bape_src.zip` contained the `results.tgz` file which contains training results and resulting model weights, these were required to export the onnx model but are not on the production instance.

I had to create a new zip file without any tgz archive or the results folder:
```zsh
zip -r bape_src.zip src/BAPE_src -x "*.tgz" "src/BAPE_src/results/*"
```

Overwrite the file in my S3 bucket:
```zsh
aws s3 cp bape_src.zip s3://onnx-deployment-phase3-artifacts-dgoossens-20250106/bape_src.zip --profile dev
```

Now around 19MB, was 330MB before.

Relaunch the t3.small instance, again with 8GB RAM.

This time the console output returned an Error during the installation of the python requirements:

```zsh
[   47.310115] cloud-init[1941]: Installing collected packages: mpmath, typing-extensions, sympy, networkx, fsspec, filelock, torch, torchaudio
[   54.975999] cloud-init[1941]: ERROR: Could not install packages due to an OSError: [Errno 28] No space left on device: '/usr/local/lib64/pyth
```

I deleted the instance, added a 2GB Swapfile to the user-data.sh script and startet it again, but ran out of space again:

```sh
aws ec2 get-console-output --target i-… --profile dev --output text

(…)
ip-10-16-2-179 login: [   15.839630] cloud-init[1939]: dd: error writing '/swapfile': No space left on device
(…)
```

So I deleted the instance, left the 2GB Swapfile in `user-data.sh` but also launched it with a 20GB GP3 EBS volume. The SSM session was established successfully:

```zsh
❯ aws ssm start-session --target i-045198a0d962d756a --profile dev                        

Starting session with SessionId: admin2026-kzun343cpikifbkqhrhifr62ui
sh-5.2$
```

#### Adjusting dependencies

But listing the root contents I couldn't find the `app.log` file, which is created at the end of the user-data, which made me assume the script breaks, so I looked into the cloud init output:

```zsh
tail -n 20 /var/log/cloud-init-output.log

(…)
ERROR: Could not find a version that satisfies the requirement click==8.3.1 (from versions: 0.1, 0.2, 0.3, 0.4, 0.5, 0.5.1, 0.6, 0.7, 1.0, 1.1, 2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.0, 3.1, 3.2, 3.3, 4.0, 4.1, 5.0, 5.1, 6.0, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7.dev0, 6.7, 7.0, 7.1, 7.1.1, 7.1.2, 8.0.0a1, 8.0.0rc1, 8.0.0, 8.0.1, 8.0.2, 8.0.3, 8.0.4, 8.1.0, 8.1.1, 8.1.2, 8.1.3, 8.1.4, 8.1.5, 8.1.6, 8.1.7, 8.1.8)
ERROR: No matching distribution found for click==8.3.1
(…)
```
On the EC2 instance the pre-installed Python 3.9 version was not compatible with the dependencies so I updated the user-data.sh script to install and use Python3.11.

I relaunched the t3.small instance with the attached 20GB GP3 SSD volume again:

Dependency issue (model_procesor.py and audio.processor.py were not copied to S3 and not downloaded via the user-data.sh):
  - uploaded missing files to S3 and updated user-data.sh script to download accordingly

-> Path issue: model not found.
Fixed path error manually on server to check API, and fixed it permanently in the user-data.sh script: 

```zsh
❯ aws ssm start-session --target i-07e342891fb3028b4 --profile dev             

Starting session with SessionId: admin2026-vfasrq78ez2txjed6qf7bzece4
```

Hot fix:
```sh
sh-5.2$ tail -f /app/app.log
2026-01-28 14:09:31,921 - API CRITICAL - FATAL: Could not load model at startup. Server will fail on requests. Error: [ONNXRuntimeError] : 3 : NO_SUCHFILE : Load model from onnx/super_param_estimator.onnx failed:Load model onnx/super_param_estimator.onnx failed. File doesn't exist
INFO:     Started server process [10555]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
^C
sh-5.2$ sudo su
[root@ip-10-16-2-92 bin]# cd /app
[root@ip-10-16-2-92 app]# mkdir onnx
[root@ip-10-16-2-92 app]# mv super_param_estimator.onnx onnx/
[root@ip-10-16-2-92 app]# pkill python3.11
[root@ip-10-16-2-92 app]# nohup python3.11 -m uvicorn api:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
[1] 11012
[root@ip-10-16-2-92 app]# tail -f app.log
nohup: ignoring input
2026-01-28 14:22:19,006 - src.model_processor INFO - Model initialized successfully.
2026-01-28 14:22:19,006 - src.model_processor INFO - Input Name: input_spectogram, Output Names: ['latent_vector', 'estimated_params', 'quantiles']
INFO:     Started server process [11012]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
curl -v http://127.0.0.1:8000/docs

q
^C
[root@ip-10-16-2-92 app]# curl -v http://127.0.0.1:8000/docs
*   Trying 127.0.0.1:8000...
* Connected to 127.0.0.1 (127.0.0.1) port 8000
* using HTTP/1.x
> GET /docs HTTP/1.1
> Host: 127.0.0.1:8000
> User-Agent: curl/8.15.0
> Accept: */*
> 
* Request completely sent off
< HTTP/1.1 200 OK
< date: Wed, 28 Jan 2026 14:28:53 GMT
< server: uvicorn
< content-length: 932
< content-type: text/html; charset=utf-8
< 

    <!DOCTYPE html>
    <html>
    <head>
    <link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
    <link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png">
    <title>BAPE API - Swagger UI</title>
    </head>
    <body>
    <div id="swagger-ui">
    </div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <!-- `SwaggerUIBundle` is now available on the page -->
    <script>
    const ui = SwaggerUIBundle({
        url: '/openapi.json',
    "dom_id": "#swagger-ui",
"layout": "BaseLayout",
"deepLinking": true,
"showExtensions": true,
"showCommonExtensions": true,
oauth2RedirectUrl: window.location.origin + '/docs/oauth2-redirect',
    presets: [
        SwaggerUIBundle.presets.apis,
        SwaggerUIBundle.SwaggerUIStandalonePreset
        ],
    })
    </script>
    </body>
    </html>
```

After I fixed the user-data.sh script to recreate the local folder structure, creating an onnx and src directory on the EC2 instance, I needed to build the encrypted connection from client to ALBs for which I first created my own dummy certificate to set up AWS Certificate Manager.

#### Setting up encrypted client-ALB connection

Create a private RSA key:
```zsh
openssl genrsa -out private.key 2048
```

Generate the cert:
```zsh
openssl req -new -x509 -sha256 -key private.key -out certificate.crt -days 10 -subj "/C=DE/ST=Berlin/L=Berlin/O=BAPE-Deployment/CN=bape-api.local" 
```

creates a self-signed X.509 certificate using the private key:

`openssl req` - certificate request utility
`-new` - create a new certificate request
`-x509` - output a self-signed certificate instead of a certificate request
`-sha256` - use SHA-256 hashing algorithm for the signature
`-key private.key` - use existing private.key
`-out certificate.crt` - save the certificate to this file
`-days 10` - certificate is valid for 10 days

The -subj flag avoids interactive prompts:

`C=DE` - Country: Germany
`ST=Berlin` - State/Province: Berlin
`L=Berlin` - Locality/City: Berlin
`O=BAPE-Deployment` - Organization name
`CN=bape-api.local` - Common Name (the domain/hostname this cert is for)

#### Upload to ACM

With private.key and certificate.crt in place we can uplaod it to AWS Certificate Manager.

```zsh
aws acm import-certificate \
--certificate fileb://certificate.crt \
--private-key fileb://private.key \
--tags Key=Name,Value=phase3-self-signed-cert \
--profile dev
```
Returns CartificateArn.

#### Create Target Group
The ALB needs a logical container it can direct to, where the EC2 instance lives.

```zsh
aws elbv2 create-target-group \
--name phase3-targets \
--protocol HTTP \
--port 8000 \
--vpc-id vpc-0772e7cc248fd716c \
--target-type instance \
--health-check-path /docs \
--health-check-interval-seconds 30 \
--profile dev
```

returns target group as JSON: ### X.13 elbv2 target groups

#### Register instance to target group

Now I can register the EC2 instance in this target group:

```zsh
aws elbv2 register-targets \
--target-group-arn arn:aws:elasticloadbalancing:eu-central-1:609662023678:targetgroup/phase3-targets/a05ae4bc1fa3a646 \
--targets Id=i-0debbaec1f3b39d10 \
--profile dev
```

retruns nothing

#### Deploy ALB across both public subnets

The ALB needs at least two subnets in two distinct AZs.
It also needs a security group which we created earlier.

```zsh
aws elbv2 create-load-balancer \
--name phase3-alb \
--subnets subnet-0e9fc06ce108ce4ea subnet-0f62225d8592a44e6 \
--security-groups sg-040e0a1163cf1f846 \
--scheme internet-facing \
--tags Key=Name,Value=phase3-alb \
--profile dev
```
returns ELBv2 as JSON, see "X.14. ELBv2"

#### Create HTTPS listener

To encrypt the input from the client to the ALB we need to add an HTTPS listener, which listens on the secure port 443 and uses the self-signed cert I just created:

```zsh
aws elbv2 create-listener \
--load-balancer-arn arn:aws:elasticloadbalancing:eu-central-1:609662023678:loadbalancer/app/phase3-alb/57debc553d5f0612 \
--protocol HTTPS --port 443 \
--certificates CertificateArn=arn:aws:acm:eu-central-1:609662023678:certificate/ebd5aa00-42da-48bd-b746-4f173221b3ee \
--default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:eu-central-1:609662023678:targetgroup/phase3-targets/a05ae4bc1fa3a646 \
--profile dev
```
returns HTTPS listener JSON, "X.15 HTTPS listener"

#### Get ALB URL

By getting the load balancer description I retrieve the Load Balancer URL.

Opening the provided DNS Name URL from the `aws elbv2 create-load-balancer …` leads to a `503 – Service Temporarily Unaivalable`

So I checked the target health:
```zsh
aws elbv2 describe-target-health \
--target-group-arn arn:aws:elasticloadbalancing:eu-central-1:609662023678:targetgroup/phase3-targets/a05ae4bc1fa3a646 \
--profile dev
```

Part of the return:
```JSON
"TargetHealth": {
                "State": "unused",
                "Reason": "Target.NotInUse",
                "Description": "Target is in an Availability Zone that is not enabled for the load balancer"
                },…
```

The ALB is spread across both publiuc subnets which are in AZ eu-central-1a and eu-central-1b, whereas the target is in eu-central-1c. but the target has to be in one of the data centers to which the ALB is registered.

So I create another Private Subnet, Private Subnet B, located in eu-central-1a.

```zsh
aws ec2 create-subnet \
--vpc-id vpc-0772e7cc248fd716c \
--cidr-block 10.16.3.0/24 \
--availability-zone eu-central-1a \
--tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=phase3-private-subnet-b}]" \
--profile dev
```

This subnet must be associated with the same private route table as public subnet A:
```zsh
aws ec2 associate-route-table \
--subnet-id subnet-01a83f167c84dde5b \
--route-table-id rtb-0d180e4bfff0d77ee \
--profile dev
```

Now I termninate the instance in Private Subnet A, to relaunch it in Private Subnet B:
```zsh
aws ec2 terminate-instances --instance-ids i-0ceed0bfeac218273 --profile dev
```

Restart in `1a`
```zsh
aws ec2 run-instances \
--image-id ami-029cdb80a7069a70a \
--instance-type t3.small \
--subnet-id subnet-01a83f167c84dde5b \
--security-group-ids sg-0eefa1fcc6557d2f8 \
--iam-instance-profile Name=phase3-ec2-profile \
--block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":20,"VolumeType":"gp3"}}]' \
--tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=phase3-prod-instance}]' \
--user-data file://user_data.sh \
--profile dev
```

This gives me a new instance-id (i-0822edff0e710f487), which I will need to register as a target.
```zsh
aws elbv2 register-targets \
--target-group-arn arn:aws:elasticloadbalancing:eu-central-1:609662023678:targetgroup/phase3-targets/a05ae4bc1fa3a646 \
--targets Id=i-0822edff0e710f487 \
--profile dev
```

Now I get a `502 - Bad Gateway` and a `elbv2 describe-target-health …` returns an `unhealthy` state but can see that the check is happening with the correct instance on the right port 8000.

I switch back to the debugging techniques I used during instance setup

```zsh
aws ssm start-session --target i-0822edff0e710f487 --profile dev
```

Inside the instance shell I could see that there was no file `app.log` which is created at server startup so the boot process must have crashed somewhere.

Since I'm already inside the instance, I can use Linux to get the cloud-init-output.log instead of `aws ec2 get-console-output`

```sh
sudo tail -n 50 /var/log/cloud-init-output.log
```

Response:
```zsh
download: s3://onnx-deployment-phase3-artifacts-dgoossens-20250106/api.py to ./api.py
download: s3://onnx-deployment-phase3-artifacts-dgoossens-20250106/requirements.txt to ./requirements.txt
download: s3://onnx-deployment-phase3-artifacts-dgoossens-20250106/bape_src.zip to ./bape_src.zip
fatal error: An error occurred (403) when calling the HeadObject operation: Forbidden
2026-02-02 12:44:07,241 - cc_scripts_user.py[WARNING]: Failed to run module scripts-user (scripts in /var/lib/cloud/instance/scripts)
2026-02-02 12:44:07,243 - util.py[WARNING]: Running module scripts-user (<module 'cloudinit.config.cc_scripts_user' from '/usr/lib/python3.9/site-packages/cloudinit/config/cc_scripts_user.py'>) failed
```

It seems like my script fails after downloading the zip… I had a mistake in the script telling the instance to download the `super_param_estimator.onnx` from within an `onnx/` *folder*, which was incorrect.
=======================================================================
-----START PERSONAL NOTES (temporary, must be deleted before prod)-----
=======================================================================

Restore Plumbing: NAT Gateway + Route Table Fix.

- allocate EIP
```zsh
aws ec2 allocate-address \
--domain vpc \
--tag-specifications "ResourceType=elastic-ip, Tags=[{Key=Name,Value=phase3-eip}]" \
--profile dev
```

Alternative: store allocation id in variable

```zsh
ALLOC_ID=$(aws ec2 allocate-address \
--domain vpc \
--tag-specifications "ResourceType=elastic-ip, Tags=[{Key=Name,Value=phase3-eip}]" \
--profile dev \
--query "AllocationId" \
--output text)
```
- create NAT GW in Public SN A

```zsh
aws ec2 create-nat-gateway \
--subnet-id subnet-0e9fc06ce108ce4ea \
--allocation-id eipalloc-02e1307aa46938763 \
--tag-specifications "ResourceType=natgateway,Tags=[{Key=Name,Value=phase3-natgw}]" \
--profile dev
```

Alternative: Store NAT Gateway ID in variable
```zsh
NAT_ID=$( \
aws ec2 create-nat-gateway \
--subnet-id subnet-0e9fc06ce108ce4ea \
--allocation-id $ALLOC_ID \
--tag-specifications "ResourceType=natgateway,Tags=[{Key=Name,Value=phase3-natgw}]" \
--profile dev \
--query 'NatGateway.NatGatewayId' \
--output text) \
echo "NAT Gateway ID: $NAT_ID"
```
- replace route

```zsh
aws ec2 replace-route \
--route-table-id rtb-0d180e4bfff0d77ee \
--destination-cidr-block 0.0.0.0/0 \
--nat-gateway-id $NAT_ID \
--profile dev
```

Launch Instance: We need the Instance ID before we can register it with the Load Balancer.

- launch instance with additional EBS volume:
```zsh
aws ec2 run-instances \
--image-id ami-029cdb80a7069a70a \
--instance-type t3.small \
--subnet-id subnet-0f8b792c550dc1f57 \ ##PAY ATTENTION TO ALB
--security-group-ids sg-0eefa1fcc6557d2f8 \
--iam-instance-profile Name=phase3-ec2-profile \
--block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":20,"VolumeType":"gp3"}}]' \
--tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=phase3-prod-instance-python311}]' \
--user-data file://user_data.sh \
--profile dev
```

current instance: i-0822edff0e710f487


Create Certificates: Generate a self-signed cert locally (openssl) and import it to AWS ACM (Certificate Manager).
Create Target Group: This is the logical container for your instances.
Register Targets: Put your running instance into that group.
Create ALB: The actual infrastructure.
Create Listener: The logic that ties it all together (Listen on 443 -> Use Cert -> Forward to Target Group).


Shut down:

aws ec2 terminate-instances --instance-ids i-0debbaec1f3b39d10 --profile dev

aws elbv2 delete-load-balancer --load-balancer-arn arn:aws:elasticloadbalancing:eu-central-1:609662023678:loadbalancer/app/phase3-alb/7e10e37d693e9f85 --profile dev

aws ec2 delete-nat-gateway --nat-gateway-id nat-0966ea833ce1a691c --profile dev

aws ec2 release-address --allocation-id eipalloc-02e1307aa46938763 --profile dev

Restart

=======================================================================
--------------------------END PERSONAL NOTES---------------------------
=======================================================================





I don't want to sink much more time into this and will use the help of AWS VPC Reachability Analyzer.


---
---

## X. Resources // As defined before and updated

### X.0. Overview

### X.1. VPC 
- name: "phase3-vpc"
- CIDR: 10.16.0.0/16
***retrieved after launch:***
- vpc-id: vpc-0772e7cc248fd716c

#### X.1.1. Subnets:
    
#### X.1.1.1. Public Subnet A (`phase3-public-subnet-a`)
- CIDR-Range: 10.16.0.0/24: 10.16.0.0 – 10.16.0.255
***retrieved after launch:***
- subnet-id: subnet-0e9fc06ce108ce4ea
- AZ: eu-central-1c
    
#### X.1.1.2. Public Subnet B (`phase3-public-subnet-b`)
- CIDR-Range: 10.16.1.0/24: 10.16.1.0 - 10.16.1.255
***retrieved after launch:***
- subnet-id: subnet-0f62225d8592a44e6
- AZ: eu-central-1b
    
#### X.1.1.3. Private Subnet A (`phase3-private-subnet-a`)
- CIDR-Range: 10.16.2.0/24: 10.16.2.0 - 10.16.2.255

***retrieved after launch:***
- subnet-id: subnet-0f8b792c550dc1f57 \
- AZ: eu-central-1c

#### X.1.1.4. Private Subnet B (`phase3-private-subnet-a`)
- CIDR-Range: 10.16.3.0/24: 10.16.3.0 - 10.16.3.255

***retrieved after launch:***
- subnet-id: subnet-01a83f167c84dde5b \
- AZ: eu-central-1a


```JSON
{
    "Subnet": {
        "AvailabilityZoneId": "euc1-az2",
        "MapCustomerOwnedIpOnLaunch": false,
        "OwnerId": "609662023678",
        "AssignIpv6AddressOnCreation": false,
        "Ipv6CidrBlockAssociationSet": [],
        "Tags": [
            {
                "Key": "Name",
                "Value": "phase3-private-subnet-b"
            }
        ],
        "SubnetArn": "arn:aws:ec2:eu-central-1:609662023678:subnet/subnet-01a83f167c84dde5b",
        "EnableDns64": false,
        "Ipv6Native": false,
        "PrivateDnsNameOptionsOnLaunch": {
            "HostnameType": "ip-name",
            "EnableResourceNameDnsARecord": false,
            "EnableResourceNameDnsAAAARecord": false
        },
        "SubnetId": "subnet-01a83f167c84dde5b",
        "State": "available",
        "VpcId": "vpc-0772e7cc248fd716c",
        "CidrBlock": "10.16.3.0/24",
        "AvailableIpAddressCount": 251,
        "AvailabilityZone": "eu-central-1a",
        "DefaultForAz": false,
        "MapPublicIpOnLaunch": false
    }
}
```




### X.2. IGW and attachment

#### X.2.1. IGW
- name: "phase3-igw"
- InternetGatewayId: igw-0ca97ba8edc60bcf4

#### X.2.2. IGW attachment
- name: "phase3-igw-attachment"

### X.3. NATGW
- name: "phase3-natgw"
- resulting from `aws ec2 create-nat-gateway`:

```JSON
{
    "ClientToken": "3853180f-9b37-4e2d-aaac-9919984338c4",
    "NatGateway": {
        "CreateTime": "2026-01-30T14:24:14+00:00",
        "NatGatewayAddresses": [
            {
                "AllocationId": "eipalloc-02e1307aa46938763",
                "IsPrimary": true,
                "Status": "associating"
            }
        ],
        "NatGatewayId": "nat-0966ea833ce1a691c",
        "State": "pending",
        "SubnetId": "subnet-0e9fc06ce108ce4ea",
        "VpcId": "vpc-0772e7cc248fd716c",
        "Tags": [
            {
                "Key": "Name",
                "Value": "phase3-natgw"
            }
        ],
        "ConnectivityType": "public"
    }
}
```




### X.4. ELB/ALB
    - "phase3-alb"

### X.5. Security Groups

#### X.5.1. **ALB Security Group**

- **Name: "phase3-sg-alb"**
- type: HTTP
- Protocol: TCP
- Source: 0.0.0.0/0
- Port: 80 (HTTP)
- Description: Allow all HTTP traffic on port 80 (SGs can onlyallow, not deny traffic).
- AZ:

*as JSON:*
```JSON
{
"GroupId": "sg-040e0a1163cf1f846",
"Tags": [
    {
        "Key": "Name",
        "Value": "phase3-sg-alb"
    }
],
"SecurityGroupArn":"arn:aws:ec2:eu-central-1:609662023678:security-groupsg-040e0a1163cf1f846"
}
```
***Rules:***
```JSON
{
    "Return": true,
    "SecurityGroupRules": [
        {
            "SecurityGroupRuleId": "sgr-0ca5877317d4f09e3",
            "GroupId": "sg-040e0a1163cf1f846",
            "GroupOwnerId": "609662023678",
            "IsEgress": false,
            "IpProtocol": "tcp",
            "FromPort": 80,
            "ToPort": 80,
            "CidrIpv4": "0.0.0.0/0",
            "SecurityGroupRuleArn": "arn:aws:ec2:eu-central-1:609662023678:security-group-rule/sgr-0ca5877317d4f09e3"
        }
    ]
}

{
    "Return": true,
    "SecurityGroupRules": [
        {
            "SecurityGroupRuleId": "sgr-081d3bec413f32b92",
            "GroupId": "sg-040e0a1163cf1f846",
            "GroupOwnerId": "609662023678",
            "IsEgress": false,
            "IpProtocol": "tcp",
            "FromPort": 443,
            "ToPort": 443,
            "CidrIpv4": "0.0.0.0/0",
            "SecurityGroupRuleArn": "arn:aws:ec2:eu-central-1:609662023678:security-group-rule/sgr-081d3bec413f32b92"
        }
    ]
}

```

#### X.5.2. **EC2 Security Group**

- **Name: "phase3-sg-ec2"**
- type: Custom TCP
- Protocol: TCP
- Source: "phase3-SG1-ALB-1", "phase3-SG3-ALB-2", 
- Port: 8000 (FastAPI)
- Description: Allow inbound traffic from ALB-1 and ALB-2 to FastAPIapp.

as JSON:
```JSON
{
"GroupId": "sg-0eefa1fcc6557d2f8",
"Tags": [
    {
        "Key": "Name",
        "Value": "phase3-sg-ec2"
    }
],
"SecurityGroupArn":"arn:aws:ec2:eu-central-1:609662023678:security-groupsg-0eefa1fcc6557d2f8"
}
```
***Rule:***
```JSON
{
    "Return": true,
    "SecurityGroupRules": [
        {
            "SecurityGroupRuleId": "sgr-0494b9e98a0011f83",
            "GroupId": "sg-0eefa1fcc6557d2f8",
            "GroupOwnerId": "609662023678",
            "IsEgress": false,
            "IpProtocol": "tcp",
            "FromPort": 8000,
            "ToPort": 8000,
            "ReferencedGroupInfo": {
                "GroupId": "sg-040e0a1163cf1f846",
                "UserId": "609662023678"
            },
            "SecurityGroupRuleArn": "arn:aws:ec2:eu-central-1:609662023678:security-group-rule/sgr-0494b9e98a0011f83"
        }
    ]
}
```


### X.6. Route Tables

#### X.6.1. Public Route Table
- Name: "phase3-public-route-table"
- rule: 0.0.0.0/0 -> IGW ("phase3-igw")
- Route Table ID: rtb-00dcbd16b07bf8e46

#### X.6.2. Private Route Table
- Name: "phase3-private-route-table"
- rule: 0.0.0.0/0 -> NATGW ("phase3-natgw")
- Route Table ID: rtb-0d180e4bfff0d77ee

#### X.6.3. Route Table Associations

- `phase3-public-route-table` with `phase3-public-subnet-a`
  - Association ID: `rtbassoc-0bda86a136481a8fb`
- `phase3-public-route-table` with `phase3-public-subnet-b`  
  - Association ID: `rtbassoc-00620f6c992fde5c3`
- `phase3-private-route-table` with `phase3-private-subnet-a`
  - Association ID: `rtbassoc-07376b41c8a4b9ce4`
- `phase3-private-route-table` with `phase3-private-subnet-b`
  - Association ID: `rtbassoc-024c1bdb4fa6538e3`

### X.7. Elastic IP 

JSON result of `aws ec2 allocate-address …`
    
```JSON
{
    "AllocationId": "eipalloc-02e1307aa46938763",
    "PublicIpv4Pool": "amazon",
    "NetworkBorderGroup": "eu-central-1",
    "Domain": "vpc",
    "PublicIp": "63.182.37.212"
}
```

### X.8. S3 bucket to store the .onnx model

result of `aws s3 mb s3://onnx-deployment-phase3-artifacts-dgoossens-20250106`

### X.9. IAM role 
result of `aws iam create-role…`

```JSON
    {
        "Role": {
            "Path": "/",
            "RoleName": "phase3-ec2-role",
            "RoleId": "AROAY34VQG77KSPJYCCNR",
            "Arn": "arn:aws:iam::609662023678:role/phase3-ec2-role",
            "CreateDate": "2026-01-07T13:59:47+00:00",
            "AssumeRolePolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "ec2.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }
        }
    }
```

### X.10. Instance Profile for the EC2 instance

### X.11. EC2 instance
result of `aws ec2 describe-instances …`

```JSON
(…)
"InstanceId": "i-0d0690e47da99c01c",
"ImageId": "ami-029cdb80a7069a70a",
(…)
```


result of `iam create-instance-profile`

```JSON
{
    "InstanceProfile": {
        "Path": "/",
        "InstanceProfileName": "phase3-ec2-profile",
        "InstanceProfileId": "AIPAY34VQG77HTGAL5JWI",
        "Arn": "arn:aws:iam::609662023678:instance-profile/phase3-ec2-profile",
        "CreateDate": "2026-01-07T14:09:02+00:00",
        "Roles": []
    }
}
``` 

#### X.11.1. DEbug Instance in Public Subnet A
`"InstanceId": "i-07cbf883226beb48a"`

### X.12. Self-signed ACM cert

result auf `aws acm import-certificate …`:

```JSON
{
    "CertificateArn": "arn:aws:acm:eu-central-1:609662023678:certificate/ebd5aa00-42da-48bd-b746-4f173221b3ee"
}
```
### X.13 elbv2 target groups
Result of `aws elbv2 create-target-group …`:

```JSON
{
    "TargetGroups": [
        {
            "TargetGroupArn": "arn:aws:elasticloadbalancing:eu-central-1:609662023678:targetgroup/phase3-targets/a05ae4bc1fa3a646",
            "TargetGroupName": "phase3-targets",
            "Protocol": "HTTP",
            "Port": 8000,
            "VpcId": "vpc-0772e7cc248fd716c",
            "HealthCheckProtocol": "HTTP",
            "HealthCheckPort": "traffic-port",
            "HealthCheckEnabled": true,
            "HealthCheckIntervalSeconds": 30,
            "HealthCheckTimeoutSeconds": 5,
            "HealthyThresholdCount": 5,
            "UnhealthyThresholdCount": 2,
            "HealthCheckPath": "/docs",
            "Matcher": {
                "HttpCode": "200"
            },
            "TargetType": "instance",
            "ProtocolVersion": "HTTP1",
            "IpAddressType": "ipv4"
        }
    ]
}
```

### X.14. ELBv2

Result of `aws elbv2 create-load-balancer …`:

```JSON
{
    "LoadBalancers": [
        {
            "LoadBalancerArn": "arn:aws:elasticloadbalancing:eu-central-1:609662023678:loadbalancer/app/phase3-alb/57debc553d5f0612",
            "DNSName": "phase3-alb-1107223156.eu-central-1.elb.amazonaws.com",
            "CanonicalHostedZoneId": "Z215JYRZR1TBD5",
            "CreatedTime": "2026-02-02T12:11:50.411000+00:00",
            "LoadBalancerName": "phase3-alb",
            "Scheme": "internet-facing",
            "VpcId": "vpc-0772e7cc248fd716c",
            "State": {
                "Code": "provisioning"
            },
            "Type": "application",
            "AvailabilityZones": [
                {
                    "ZoneName": "eu-central-1b",
                    "SubnetId": "subnet-0f62225d8592a44e6",
                    "LoadBalancerAddresses": []
                },
                {
                    "ZoneName": "eu-central-1a",
                    "SubnetId": "subnet-0e9fc06ce108ce4ea",
                    "LoadBalancerAddresses": []
                }
            ],
            "SecurityGroups": [
                "sg-040e0a1163cf1f846"
            ],
            "IpAddressType": "ipv4"
        }
    ]
}
```

### X.15. HTTPS listener

Result of `aws elbv2 create-listener …``

```JSON
{
    "Listeners": [
        {
            "ListenerArn": "arn:aws:elasticloadbalancing:eu-central-1:609662023678:listener/app/phase3-alb/57debc553d5f0612/f736d51e97cc34f9",
            "LoadBalancerArn": "arn:aws:elasticloadbalancing:eu-central-1:609662023678:loadbalancer/app/phase3-alb/57debc553d5f0612",
            "Port": 443,
            "Protocol": "HTTPS",
            "Certificates": [
                {
                    "CertificateArn": "arn:aws:acm:eu-central-1:609662023678:certificate/ebd5aa00-42da-48bd-b746-4f173221b3ee"
                }
            ],
            "SslPolicy": "ELBSecurityPolicy-2016-08",
            "DefaultActions": [
                {
                    "Type": "forward",
                    "TargetGroupArn": "arn:aws:elasticloadbalancing:eu-central-1:609662023678:targetgroup/phase3-targets/a05ae4bc1fa3a646",
                    "ForwardConfig": {
                        "TargetGroups": [
                            {
                                "TargetGroupArn": "arn:aws:elasticloadbalancing:eu-central-1:609662023678:targetgroup/phase3-targets/a05ae4bc1fa3a646",
                                "Weight": 1
                            }
                        ],
                        "TargetGroupStickinessConfig": {
                            "Enabled": false
                        }
                    }
                }
            ]
        }
    ]
}
```

## X+1. Learnings and lookout for phase 4.