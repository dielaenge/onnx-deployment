Phase 2. ## Naive cloud deployment via AWS Console

Initial Instance Configuration via AWS Console

**Date:** 2025-10-27 - 2025-11-01

### 1. Decision: EC2 Architecture and Instance Type

*   **Choice:**
    *   **Name/Tags:** `Name: onnx-acoustic-api-naive-EC2-deployment`, `project_phase: 2` for cost tracking.
    *   **AMI:** Amazon Linux 2023 (`x86_64` architecture).
    *   **Instance Type:** `t2.micro` (1 GiB RAM, 1 vCPU).
*   **Justification:**
    *   The primary constraint for this learning phase is minimizing cost. The `t2.micro` is eligible for the AWS Free Tier and meets the project's minimum memory requirement of >210 MiB, providing a safe buffer for the OS and application runtime.
    *   Amazon Linux 2023 is chosen as it's a modern, AWS-supported default, ensuring up-to-date packages and security patches.
*   **Alternatives Considered:**
    *   `t4g.micro` (Graviton/arm64): This instance offers superior price-to-performance outside the free tier. It was not chosen for this initial phase to strictly adhere to Free Tier eligibility but is noted as the preferred choice for a cost-optimized production deployment.

### 2. Decision: Network Security (Security Groups)

*   **Choice:** A single Security Group will be created for the instance with two specific inbound rules:
    1.  **Rule 1 (SSH for Management):** Allow traffic on `TCP Port 22` from `My IP` only.
    2.  **Rule 2 (HTTP for Application):** Allow traffic on `TCP Port 8000` from `0.0.0.0/0` (anywhere).
*   **Justification:**
    *   A single Security Group is used to manage all firewall rules for this instance, which is standard practice.
    *   SSH access (Port 22) is restricted to my personal IP to follow the principle of least privilege and prevent unauthorized access attempts.
    *   The application port (`8000`) is opened to the public internet (`0.0.0.0/0`) to allow testing of the API. This matches the port the `uvicorn` server is configured to listen on in `api.py`.
*   **Alternatives Considered:**
    *   Opening Port 80 (standard HTTP) was considered but rejected because the application is not configured to run on that port. In a later phase, a Load Balancer will be used to accept traffic on Port 80/443 and forward it to the instance on Port 8000.

### 3. Decision: Instance Access Method (SSH)

*   **Choice:** EC2 Key Pair (standard SSH).
*   **Justification:** For this "naive" deployment phase, using a standard, manually-managed EC2 Key Pair is the most direct way to understand the fundamentals of EC2 authentication. I will create a new key pair, download the `.pem` file, and use it to connect via my local SSH client.
*   **Alternatives Considered:**
    *   **Systems Manager Session Manager:** This is a more secure, modern approach that avoids SSH key management. It will be implemented in a later "production-like" phase to demonstrate best practices.

### 4. Decision: Instance Bootstrapping, Code Deployment and Testing

*   **Problem:** 
A bare EC2 instance must be configured manually with the required dependencies and application to experience the friction of manual deployment.
*   **Decision: Model file handling**
    *   **Choice:** The `dummy_acoustic_model.onnx` file was generated locally and committed to the Git repository. It was then deployed to the instance via `git clone`.
    *   **Justification:** The dummy model is a small, but essential artifact. Creating it locally and committing it to the repository is simpler than installing `torch` and other large dependencies on the server to create it in the cloiud environment. This keeps the production environment lean.
*   **Decision 2: What needs to be configured and how**
    *   **Choice:** We will access the instance via SSH and run all commands manually in a single SSH session: updating the server, installing necessary system packages and python, cloning the app code from our git repository including the onnx model and finally start our app.
    *   **Justification:** The manual process is intentended as it highlights the friction and error potential, making a case for the automation in later phases.
*   **Challenge & Investigation: `ffmpeg` Dependency Failure** 
    The initial plan, using `dnf` to install `git`, `pip` and `ffmpeg` failed:
    1.  `dnf` could not find packages named `python-pip3` or `ffmpeg`.
    2.  Investigation with `dnf search python` revealed the correct package name was `python3-pip`.
    3.  Further investigation revealed that `ffmpeg` is not available in the default Amazon Linux 2023 repositories. The standard solution for CentOS/RHEL (EPEL repository) is not compatible with AL2023. The solution for Fedora (RPM Fusion) also failed due to `system-release` dependency conflicts.
*   **Decision 3: How to install a static binary prebuild of FFmpeg to process multimedia files on AL2023**
    *   **Choice:** 
    Setting up the server instance required me to switch from my local arm64 platform to a well supported official Amzaon Linux AMI (`x86_64`). Setting it up I learned that MacOS systems have the required FFmpeg multimedia framework preinstalled but the AL2023 AMI does not, so my app crashed on the EC2 instance. Looking for a solution, I could have used a preconfigured AMI which comes with the framework preinstalled or I could search for a *rawer* solution which would allow me to understand more. This solution, I found when searching for `Install ffmpeg on Amazon Linux 2023 AMI` on [willmasters' GitHub Gist page](https://gist.github.com/willmasters/382fe6caba44a4345a3de95d98d3aae5). As I was looking for the right tarball archive with a static build on [johnvansickle.com](https://johnvansickle.com/ffmpeg/), I learned that `amd64` is the term for `x86_64` architectures. This is reflected in the Manual Runbook further down.
    *   **Justification:** 
    This approach is self-contained and works without managing complex third-party repositories. For this use case it proved to be an effective problem-solving strategy.
*   **Manual Runbook:**
        ```ssh
        # 1. SSH into the instance
        # ssh -i ~/.ssh/your-key.pem ec2-user@<PUBLIC_IP_OF_EC2-INSTANCE>

        # 2. Update packages and install git / pip
        sudo dnf update -y    
        sudo dnf install git python3-pip -y

        # 3. Find out system architecture, download and install ffmpeg static binary
        uname -a # use to identify right build
        # create folder for tar, switch into it and download
        mkdir sources && cd sources
        wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz #link copied from website https://johnvansickle.com/ffmpeg/
        # extract tar
        tar -xf ffmpeg-git-amd64-static.tar.xz
        # will create a folder with name including the release number -> use tab completion to switch into folder
        cd ffmpeg-git-*-amd64-static
        #copy static builds to `usr/local/bin/` (local folder for executables, typically isntalled by sysadmin or user / not managed by OS's package manager / for software excluded from base OS distribution, e.g. custom-compiled programs, third-party applications, or locally developed scripts)
        sudo cp ffmpeg ffprobe /usr/local/bin/

        # 4. Clone repo, install dependencies, and run the app
        cd ~
        git clone https://github.com/dielaenge/onnx-deployment
        cd onnx-deployment
        pip3 install -r requirements.txt
        python3 api.py
        ```

*   **Client-Side Testing:**
    *   **Challenge:** 
    Initial `curl` tests failed with a `400 Bad Request`. Investigation showed this was due to the client not sending the `Content-Type` header, which the API requires for validation.
    *   **Solution:** 
    The final `curl` command explicitly sets the file's MIME type:
    ```SSH
    curl -X POST -F "audio_file=@temp/ouch.wav;type=audio/wav" http://<PUBLIC_IP_OF_EC2-INSTANCE>:8000/acou-vec/generate
    ```

*   **Phase Completion & Cleanup:**
    *   The running application was stopped (`CTRL+C`).
    *   The EC2 instance was **terminated** via the AWS Console to stop all billing.
    *   This log was updated to reflect the final, successful process.