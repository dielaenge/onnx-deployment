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



   


