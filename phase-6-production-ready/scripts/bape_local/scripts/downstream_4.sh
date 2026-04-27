#!/bin/bash

export PYTHONPATH="$(pwd):PYTHONPATH"

# proposed (fixed)
CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=t60 \
    subdir=prop/t60 \
    model.encoder_state=logs/speech_encoder/2025-11-03_17-27-17/model.pth \
    model.freeze_encoder=true \
    model.reset_encoder=false \
    model.estimator.output_dim=7 \
    model.estimator.output_act=relu

CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=c50 \
    subdir=prop/c50 \
    model.encoder_state=logs/speech_encoder/2025-11-03_17-27-17/model.pth \
    model.freeze_encoder=true \
    model.reset_encoder=false \
    model.estimator.output_dim=7 \
    model.estimator.output_act=null

CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=edt \
    subdir=prop/edt \
    model.encoder_state=logs/speech_encoder/2025-11-03_17-27-17/model.pth \
    model.freeze_encoder=true \
    model.reset_encoder=false \
    model.estimator.output_dim=7 \
    model.estimator.output_act=relu

CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=mag_oct \
    subdir=prop/mag \
    model.encoder_state=logs/speech_encoder/2025-11-03_17-27-17/model.pth \
    model.freeze_encoder=true \
    model.reset_encoder=false \
    model.estimator.output_dim=6 \
    model.estimator.output_act=null


# proposed (fine-tuned)
CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=t60 \
    subdir=prop_ft/t60 \
    trainer.optimizer.lr=0.00005 \
    model.encoder_state=logs/speech_encoder/2025-11-03_17-27-17/model.pth \
    model.freeze_encoder=false \
    model.reset_encoder=false \
    model.estimator.output_dim=7 \
    model.estimator.output_act=relu

CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=c50 \
    subdir=prop_ft/c50 \
    trainer.optimizer.lr=0.00005 \
    model.encoder_state=logs/speech_encoder/2025-11-03_17-27-17/model.pth \
    model.freeze_encoder=false \
    model.reset_encoder=false \
    model.estimator.output_dim=7 \
    model.estimator.output_act=null

CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=edt \
    subdir=prop_ft/edt \
    trainer.optimizer.lr=0.00005 \
    model.encoder_state=logs/speech_encoder/2025-11-03_17-27-17/model.pth \
    model.freeze_encoder=false \
    model.reset_encoder=false \
    model.estimator.output_dim=7 \
    model.estimator.output_act=relu

CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=mag_oct \
    subdir=prop_ft/mag \
    trainer.optimizer.lr=0.00005 \
    model.encoder_state=logs/speech_encoder/2025-11-03_17-27-17/model.pth \
    model.freeze_encoder=false \
    model.reset_encoder=false \
    model.estimator.output_dim=6 \
    model.estimator.output_act=null



# end-to-end
CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=t60 \
    subdir=e2e/t60 \
    trainer.optimizer.lr=0.0002 \
    model.encoder_state=logs/speech_encoder/2025-11-03_17-27-17/model.pth \
    model.freeze_encoder=false \
    model.reset_encoder=true \
    model.estimator.output_dim=7 \
    model.estimator.output_act=relu

CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=c50 \
    subdir=e2e/c50 \
    trainer.optimizer.lr=0.0002 \
    model.encoder_state=logs/speech_encoder/2025-11-03_17-27-17/model.pth \
    model.freeze_encoder=false \
    model.reset_encoder=true \
    model.estimator.output_dim=7 \
    model.estimator.output_act=null

CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=edt \
    subdir=e2e/edt \
    trainer.optimizer.lr=0.0002 \
    model.encoder_state=logs/speech_encoder/2025-11-03_17-27-17/model.pth \
    model.freeze_encoder=false \
    model.reset_encoder=true \
    model.estimator.output_dim=7 \
    model.estimator.output_act=relu

CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=mag_oct \
    subdir=e2e/mag \
    trainer.optimizer.lr=0.0002 \
    model.encoder_state=logs/speech_encoder/2025-11-03_17-27-17/model.pth \
    model.freeze_encoder=false \
    model.reset_encoder=true \
    model.estimator.output_dim=6 \
    model.estimator.output_act=null



# semi-blind
CUDA_VISIBLE_DEVICES=1 python src/train_param_nb.py \
    target=t60 \
    subdir=sb/t60 \
    model.encoder_state=logs/vae/2025-10-15_15-51-12/model.pth \
    model.freeze_encoder=true \
    model.estimator.output_dim=7 \
    model.estimator.output_act=relu

CUDA_VISIBLE_DEVICES=1 python src/train_param_nb.py \
    target=c50 \
    subdir=sb/c50 \
    model.encoder_state=logs/vae/2025-10-15_15-51-12/model.pth \
    model.freeze_encoder=true \
    model.estimator.output_dim=7 \
    model.estimator.output_act=null

CUDA_VISIBLE_DEVICES=1 python src/train_param_nb.py \
    target=edt \
    subdir=sb/edt \
    model.encoder_state=logs/vae/2025-10-15_15-51-12/model.pth \
    model.freeze_encoder=true \
    model.estimator.output_dim=7 \
    model.estimator.output_act=relu

CUDA_VISIBLE_DEVICES=1 python src/train_param_nb.py \
    target=mag_oct \
    subdir=sb/mag \
    model.encoder_state=logs/vae/2025-10-15_15-51-12/model.pth \
    model.freeze_encoder=true \
    model.estimator.output_dim=6 \
    model.estimator.output_act=null


# non-blind
CUDA_VISIBLE_DEVICES=1 python src/train_param_nb.py \
    target=t60 \
    subdir=nb/t60 \
    model.encoder_state=logs/vae/2025-10-15_15-51-12/model.pth \
    model.freeze_encoder=false \
    model.estimator.output_dim=7 \
    model.estimator.output_act=relu

CUDA_VISIBLE_DEVICES=1 python src/train_param_nb.py \
    target=c50 \
    subdir=nb/c50 \
    model.encoder_state=logs/vae/2025-10-15_15-51-12/model.pth \
    model.freeze_encoder=false \
    model.estimator.output_dim=7 \
    model.estimator.output_act=null

CUDA_VISIBLE_DEVICES=1 python src/train_param_nb.py \
    target=edt \
    subdir=nb/edt \
    model.encoder_state=logs/vae/2025-10-15_15-51-12/model.pth \
    model.freeze_encoder=false \
    model.estimator.output_dim=7 \
    model.estimator.output_act=relu

CUDA_VISIBLE_DEVICES=1 python src/train_param_nb.py \
    target=mag_oct \
    subdir=nb/mag \
    model.encoder_state=logs/vae/2025-10-15_15-51-12/model.pth \
    model.freeze_encoder=false \
    model.estimator.output_dim=6 \
    model.estimator.output_act=null

# ###############################################################################

# ctr (fixed)
CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=t60 \
    subdir=ctr_param/t60 \
    model.encoder_state=logs/ctr/2025-11-03_20-08-03/model.pth \
    model.freeze_encoder=true \
    model.reset_encoder=false \
    model.estimator.output_dim=7 \
    model.estimator.output_act=relu

CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=c50 \
    subdir=ctr_param/c50 \
    model.encoder_state=logs/ctr/2025-11-03_20-08-03/model.pth \
    model.freeze_encoder=true \
    model.reset_encoder=false \
    model.estimator.output_dim=7 \
    model.estimator.output_act=null

CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=edt \
    subdir=ctr_param/edt \
    model.encoder_state=logs/ctr/2025-11-03_20-08-03/model.pth \
    model.freeze_encoder=true \
    model.reset_encoder=false \
    model.estimator.output_dim=7 \
    model.estimator.output_act=relu

CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=mag_oct \
    subdir=ctr_param/mag \
    model.encoder_state=logs/ctr/2025-11-03_20-08-03/model.pth \
    model.freeze_encoder=true \
    model.reset_encoder=false \
    model.estimator.output_dim=6 \
    model.estimator.output_act=null


# ctr (fine-tuned)
CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=t60 \
    subdir=ctr_param_ft/t60 \
    trainer.optimizer.lr=0.00005 \
    model.encoder_state=logs/ctr/2025-11-03_20-08-03/model.pth \
    model.freeze_encoder=false \
    model.reset_encoder=false \
    model.estimator.output_dim=7 \
    model.estimator.output_act=relu

CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=c50 \
    subdir=ctr_param_ft/c50 \
    trainer.optimizer.lr=0.00005 \
    model.encoder_state=logs/ctr/2025-11-03_20-08-03/model.pth \
    model.freeze_encoder=false \
    model.reset_encoder=false \
    model.estimator.output_dim=7 \
    model.estimator.output_act=null

CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=edt \
    subdir=ctr_param_ft/edt \
    trainer.optimizer.lr=0.00005 \
    model.encoder_state=logs/ctr/2025-11-03_20-08-03/model.pth \
    model.freeze_encoder=false \
    model.reset_encoder=false \
    model.estimator.output_dim=7 \
    model.estimator.output_act=relu

CUDA_VISIBLE_DEVICES=1 python src/train_param.py \
    target=mag_oct \
    subdir=ctr_param_ft/mag \
    trainer.optimizer.lr=0.00005 \
    model.encoder_state=logs/ctr/2025-11-03_20-08-03/model.pth \
    model.freeze_encoder=false \
    model.reset_encoder=false \
    model.estimator.output_dim=6 \
    model.estimator.output_act=null