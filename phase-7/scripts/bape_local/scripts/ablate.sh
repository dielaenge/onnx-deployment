#!/bin/bash

export PYTHONPATH="$(pwd):PYTHONPATH"

# proposed (fixed)
CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=t60 \
    subdir=ablate \
    model.encoder_state=logs/ctr/2025-10-08_00-39-43/model.pth \
    model.freeze_encoder=true \
    model.estimator.output_dim=7 \
    model.estimator.output_act=relu

CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=t60 \
    subdir=ablate \
    model.encoder_state=logs/ctr/2025-10-08_16-29-46/model.pth \
    model.freeze_encoder=true \
    model.estimator.output_dim=7 \
    model.estimator.output_act=relu

CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=t60 \
    subdir=ablate \
    model.encoder_state=logs/ctr/2025-10-09_07-36-25/model.pth \
    model.freeze_encoder=true \
    model.estimator.output_dim=7 \
    model.estimator.output_act=relu

CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=t60 \
    subdir=ablate \
    model.encoder_state=logs/ctr/2025-10-09_23-54-11/model.pth \
    model.freeze_encoder=true \
    model.estimator.output_dim=7 \
    model.estimator.output_act=relu