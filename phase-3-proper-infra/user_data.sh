#!/bin/bash

set -e # exit if a command fails

# Create 2GB of swap space to prevent OOM
dd if=/dev/zero of=/swapfile bs=128M count=16
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# 1. Update and install system tools (explicitly Python3.11 for interoperability)
dnf update -y
dnf install -y  python3.11 python3.11-pip unzip wget

# 2. Install SSM-Agent
dnf install -y amazon-ssm-agent
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent

# 3. Install static binary of FFMPEG (learned during phase2[LINK!] about necessity)
# switch into 
cd /usr/local/bin
# download
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
# unzip file and strip parent folder bape_src
tar -xf ffmpeg-release-amd64-static.tar.xz --strip-components=1
# remove download
rm ffmpeg-release-amd64-static.tar.xz

# 4. Create application directory and open it
mkdir -p /app
cd /app
# create src and onnx directories
mkdir -p onnx
mkdir -p src
mkdir -p static

# 5. Download artifacts (model, BAPE submodule, api.py and requiremts.txt)
BUCKET="s3://onnx-deployment-phase3-artifacts-dgoossens-20250106"
aws s3 cp $BUCKET/api.py .
aws s3 cp $BUCKET/requirements.txt .
aws s3 cp $BUCKET/bape_src.zip .
aws s3 cp $BUCKET/super_param_estimator.onnx onnx/super_param_estimator.onnx
aws s3 cp $BUCKET/src/audio_processor.py src/audio_processor.py
aws s3 cp $BUCKET/src/model_processor.py src/model_processor.py
aws s3 cp $BUCKET/static/index.html static/index.html

# 6. unzip submodule
unzip bape_src.zip

# 7. Install dependencies

#first install CPU-only dependencies for torch to save space and time
#our t3.small EC2 instance won't have a GPU, we rely on CPU only #we download from an explicit url because not specifying also downloads the cuda backend 
#this explicit download step is separated from the following dependency installations to prevent conflicts
pip3.11 install torch==2.2.2 torchaudio==2.2.2 --index-url https://download.pytorch.org/whl/cpu

#install remaining dependencies from file
pip3.11 install -r requirements.txt

# 7. Start the application
#`nohup` to ignore hang up, because user_data.sh closes after running which would also close the shell and any launched processes
#uvicorn starts the web server and accepts any connetctions (0.0.0.0)
# `> app.log` wites all print statements to app.log
# `2>&1`: Linux output streams 1 (standard/success) and 2 (errors) are merged into app.log // command redirects 2 into 1
# `&` Ampersand makes the command a background process
nohup python3.11 -m uvicorn api:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &