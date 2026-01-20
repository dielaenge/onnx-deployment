#!/bin/bash

set -e # exit if a command fails

# 1. Update and install system tools
dnf update -y
dnf install -y  python3-pip unzip wget

# 2. Install static binary of FFMPEG (learned during phase2[LINK!] about necessity)
# switch into 
cd /usr/local/bin
# download
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
# unzip file and strip parent folder bape_src
tar -xf ffmpeg-release-amd64-static.tar.xz --strip-components=1
# remove download
rm ffmpeg-release-amd64-static.tar.xz

# 3. Create application directory and open it
mkdir -p /app
cd /app

# 4. Download artifacts (model, BAPE submodule, api.py and requiremts.txt)
aws s3 cp s3://onnx-deployment-phase3-artifacts-dgoossens-20250106/api.py
aws s3 cp s3://onnx-deployment-phase3-artifacts-dgoossens-20250106/requirements.txt
aws s3 cp s3://onnx-deployment-phase3-artifacts-dgoossens-20250106/super_param_estimator.onnx
aws s3 cp s3://onnx-deployment-phase3-artifacts-dgoossens-20250106/bape_src.zip

# 5. unzip submodule
unzip bape_src.zip

# 6. Install dependencies

#first install CPU-only dependencies for torch to save space and time
#our t3.small EC2 instance won't have a GPU, we rely on CPU only #we download from an explicit url because not specifying also downloads the cuda backend 
#this explicit download step is separated from the following dependency installations to prevent conflicts
pip3 install torch==2.2.2 torchaudio==2.2.2 --index-url https://download.pytorch.org/whl/cpu

#install remaining dependencies from file
pip3 install -r requirements.txt

# 7. Start the application
#`nohup` to ignore hang up, because user_data.sh closes after running which would also close the shell and any launched processes
#uvicorn starts the web server and accepts any connetctions (0.0.0.0)
# `> app.log` wites all print statements to app.log
# `2>&1`: Linux output streams 1 (standard/success) and 2 (errors) are merged into app.log // command redirects 2 into 1
# `&` Ampersand makes the command a background process
nohup python3 -m uvicorn --host 0.0.0.0 --port 8000 > app.log 2>&1 &