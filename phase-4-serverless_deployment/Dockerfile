# Use the AWS managed base image for Python 3.11
FROM public.ecr.aws/lambda/python:3.11

# to make this compatible with my tooling, especially FastAPI, I use the aws lambda adapter
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter

#install tar xz unzip and libsndfile
RUN yum install -y tar xz gzip unzip libsndfile \
    # download ffmpeg build
    && curl -L -o ffmpeg.tar.xz  https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    # unzip file
    && tar -xf ffmpeg.tar.xz \
    # move to /usr/bin/ffmpeg
    && mv ffmpeg-*-amd64-static/ffmpeg /usr/bin/ffmpeg \
    # remove anything ffmpeg from th root folder
    && rm -rf ffmpeg* \
    && yum clean all

# install CPU-only dependencies for torch to save space and time / download from explicit url to avoid dowonloading cuda backend; step separated from dependency installations to prevent conflicts
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --upgrade pip \ 
    && pip install torch==2.2.2 torchaudio==2.2.2 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

WORKDIR ${LAMBDA_TASK_ROOT}

# copy app
COPY onnx/ ${LAMBDA_TASK_ROOT}/onnx
COPY static/ ${LAMBDA_TASK_ROOT}/static
COPY src/ ${LAMBDA_TASK_ROOT}/src
COPY api.py ${LAMBDA_TASK_ROOT}

ENV PORT=8080

# Clear the AWS Entrypoint so we can run uvicorn directly
ENTRYPOINT []

# 7. Start the application
# look for the app object in api.py
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]