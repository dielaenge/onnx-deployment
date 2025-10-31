# ***Content and structure until line 102 must be rewritten to reflect desicions!!***
# ***Valid data from line 102***

# Process and findings of the onnx-acoustic project
*Documentation*

1. ## Local foundation with placeholder model

   see materials in notes.md

2. ## Naive cloud deployment

Initial Instance Configuration

**Date:** 2023-10-27

### 1. Decision: EC2 Architecture and Instance Type

*   **Choice:**
    *   **AMI:** Amazon Linux 2023 (x86_64 architecture).
    *   **Instance Type:** `t2.micro` (1 GiB RAM, 1 vCPU).
*   **Justification:**
    *   The primary constraint for this learning phase is minimizing cost. The `t2.micro` is eligible for the AWS Free Tier and meets the project's minimum memory requirement of >210 MiB, providing a safe buffer for the OS and application runtime.
    *   Amazon Linux 2023 is chosen as it's a modern, AWS-supported default, ensuring up-to-date packages and security patches.
*   **Alternatives Considered:**
    *   `t4g.micro` (Graviton/arm64): This instance offers superior price-to-performance. It was not chosen for this initial phase to strictly adhere to Free Tier eligibility but is noted as the preferred choice for a cost-optimized production deployment.

### 2. Decision: Network Security (Security Group)

*   **Choice:** A single Security Group will be created for the instance with two specific inbound rules:
    1.  **Rule 1 (SSH for Management):** Allow traffic on `TCP Port 22` from `My IP` only.
    2.  **Rule 2 (HTTP for Application):** Allow traffic on `TCP Port 8000` from `0.0.0.0/0` (anywhere).
*   **Justification:**
    *   A single Security Group is used to manage all firewall rules for this instance, which is standard practice.
    *   SSH access (Port 22) is restricted to my personal IP to follow the principle of least privilege and prevent unauthorized access attempts.
    *   The application port (`8000`) is opened to the public internet (`0.0.0.0/0`) to allow testing of the API. This matches the port the `uvicorn` server is configured to listen on in `api.py`.
*   **Alternatives Considered:**
    *   Opening Port 80 (standard HTTP) was considered but rejected because the application is not configured to run on that port. In a later phase, a Load Balancer will be used to accept traffic on Port 80/443 and forward it to the instance on Port 8000.

### 3. Decision: Instance Access Method

*   **Choice:** EC2 Key Pair (standard SSH).
*   **Justification:** For this "naive" deployment phase, using a standard, manually-managed EC2 Key Pair is the most direct way to understand the fundamentals of EC2 authentication. I will create a new key pair, download the `.pem` file, and use it to connect via my local SSH client.
*   **Alternatives Considered:**
    *   **Systems Manager Session Manager:** This is a more secure, modern approach that avoids SSH key management. It will be implemented in a later "production-like" phase to demonstrate best practices.


### 4. Decision: Setting up the EC2 instance
*   **1. Name and tags:** I created two tags, my main thought here, was to identify the deployment in general but be able to create billing analysis based on project phase:
      1. Name: `onnx-acoustic-api-naive-EC2-deployment`
      2. `project_phase`: `2`
    **2. AMI:** I'm using the first suggested QuickStart AMI: Amazon Linux 2023 kernel-6.1 and I choose 64-bit, `x86_64`, architecture because I want to use a `t2.micro` instance which is free tier eligible.
    **3. Instance family and type:** As mentioned: `t2.micro`. It is free tier eligible and has enough memory to run our dummy model.
    **4.Instance Access:**I will create a new key pair
      1. Key pair name: `onnx-acoustic-naive-ec2-deployment`
      2. Key pair type: `RSA` (don't know why)
      3. Private key file format: .pem (because it's compatible with SSH)
      4. I'll immediately save it to a hidden folder outside the project like `~/.ssh/`
    **5. Networking:** 
      1. I'll choose the default vpc which has a CIDR of `172.31.0.0/16`
      2. I'll name the security group onnx-acoustic-sg
      3. I'll create two inbound sg rules:
        1. SSH Access 
        - Type: SSH
        - Source: [My IP]
        - Protocol: TCP
        - Port: 22
        - Description: SSH for admin desktop
        2. HTTP Access
        - Type: Custom TCP
        - Source: 0.0.0.0/0
        - Protocol: TCP
        - Port: 8000 (as defined in our uvicorn.run() command)

### 5. Decision: Instance Bootstrapping and Code Deployment

**Date:** 2023-10-29

*   **Problem:** For the naive deployment a bare EC2 instance needs to be configured with the required dependencies and app code before the API can run. 
We will first do this manually via SSH to experience the repetitiveness and error proness. In a next step we will use the UserData script to automate this.

*   **Decision 1: Model file handling**
    *   **Choice:** We will create the dummy model in our local repository and then `git clone` it to our instance later.
    *   **Justification:** During the local deployment I created a script to create a dummy onnx model which I then used as a placeholder model. As this model creation is not an important deliverable in the project but just a helper tool which will then be replaced by the *real* model of my collaborator, it's more efficient to only have the dummy onnx model as part of the repository and then later replace it with the real model. Furthermore, running the script locally avoids downloading large model creation dependencies like `torch` to our instance. The `create_dummy_model.py` thus stays local.

*   **Decision 2: What needs to be configured and how?**
    *   **Choice:** We will access the instance via SSH and run all commands manually in a single SSH session: updating the server,install necessary system packages and python, cloning the app code from our git repository including the onnx model and finally start our app.
    *   **Justification:** The manual process is intentional as it highlights the friction and error potential, making a case for the automation in later phases.

    *   **bash commands:**
        ```bash
        # 1. Update all preinstalled packages to their latest versions (and confirm all occuring dialogs)
        sudo dnf update -y

        # 2. Install required system packages (git, ffmpeg, python-pip3 - Python3.9 is preinstalled on AL2023 AMIs) and confirm all occuring dialogs
        sudo dnf install ffmpeg git python3-pip -y
 
        # 3. Clone project repository from url
        
        sudo git clone https://github.com/dielaenge/onnx-deployment.git
        
        # 4. Switch into project folder and install requirements
        
        cd onnx-acoustic/

        pip3 install -r requirements.txt

        # 5. Start the FastAPI application

        python3 api.py
        ```

*   **Decision 3: Setting up the AL 2023 server**
    *   **Choice:** Setting up the server instance required me to switch from my local arm64 platform to a well supported official Amzaon Linux AMI. Setting it up I learned that MacOS systems has the FFmpeg multimedia framework preinstalled but athe AL2023 instance does not, so my app crashed on the EC2 instance.
    Looking for a solution, I could have used a preconfigured AMI which comes with the framework preinstalled or I could search for another solution which I found when searching for `Install ffmpeg on Amazon Linux 2023 AMI` on [GitHub Gist](https://gist.github.com/willmasters/382fe6caba44a4345a3de95d98d3aae5)
    

