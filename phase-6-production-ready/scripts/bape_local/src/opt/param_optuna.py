import os
from collections import deque

import torch
import torch.nn as nn
import torch.nn.functional as F
from hydra import compose, initialize
from hydra.utils import instantiate
from torch.utils.tensorboard import SummaryWriter
from omegaconf import DictConfig, OmegaConf
import optuna

from src.data.datamodule import DataModule
from src.util.utils import get_device, create_log_dir
from src.util.loss import quantile_loss


def step(model, batch, target, device):
    """Single training step for parameter estimation."""
    _, _, _, _, wetspec, _, _, snr, param = batch

    wetspec = wetspec.to(device)
    gt = param[target].to(device)

    est, quant_conf = model(wetspec)
    quant = torch.stack([est[..., 0], est[..., -1]], dim=2)

    loss = quantile_loss(est, gt)

    return {
        "loss": loss,
        "gt": gt,
        "est": est,
        "quant": quant,
        "quant_conf": quant_conf,
        "snr": snr,
        "param": param,
    }


def train_with_config(cfg: DictConfig) -> float:
    """Train model with given config and return best validation loss."""

    device = get_device("cuda")

    if torch.backends.cudnn.is_available():
        torch.backends.cudnn.benchmark = True

    log_dir, _ = create_log_dir(subdir="hpo_param", debug=cfg.debug)

    # write config file to logdir
    OmegaConf.save(config=cfg, f=os.path.join(log_dir, "config.yaml"))

    # instantiate the model and data module
    data: DataModule = instantiate(cfg.data)
    model: nn.Module = instantiate(cfg.model)

    # instantiate optimizer and scheduler
    optimizer = instantiate(cfg.trainer.optimizer, params=model.parameters())
    scheduler = (
        instantiate(cfg.trainer.scheduler, optimizer=optimizer)
        if cfg.trainer.scheduler is not None
        else None
    )

    # move model to device
    model.to(device)

    # logging and early stopping stuff
    logger = SummaryWriter(log_dir)
    step_idx, stag_ct, best_val_loss = 0, 0, 1e10

    # init calibration set for conformal prediction
    calibration_set = deque()

    # target parameter
    target = cfg.target

    try:
        for epoch in range(cfg.trainer.max_epochs):
            logger.add_scalar("epoch", epoch, step_idx)

            batch_idx, train_loss = 0, 0
            model.train()

            # training loop
            for batch in data.train_loader:
                optimizer.zero_grad()
                step_dict = step(model, batch, target, device)
                loss = step_dict["loss"]
                loss.backward()
                optimizer.step()

                train_loss += loss.item()
                step_idx += 1
                batch_idx += 1

            train_loss /= batch_idx

            # validation loop
            model.eval()
            batch_idx, val_loss = 0, 0
            for batch in data.valid_loader:
                with torch.no_grad():
                    step_dict = step(model, batch, target, device)
                    loss = step_dict["loss"]

                    # gather calibration set for conformal prediction
                    calibration_set.append(
                        {"gt": step_dict["gt"], "quant": step_dict["quant"]}
                    )

                    val_loss += loss.item()
                    batch_idx += 1

            val_loss /= batch_idx
            logger.add_scalar("loss/valid_epoch", val_loss, step_idx)

            # update prediction interval adjustment
            gt = torch.cat([batch["gt"] for batch in calibration_set])
            lower = torch.cat([batch["quant"][:, 0] for batch in calibration_set])
            upper = torch.cat([batch["quant"][:, -1] for batch in calibration_set])
            model.conformalize_quantiles(gt, lower, upper)
            calibration_set.clear()

            # update scheduler
            if scheduler is not None:
                scheduler.step(val_loss)

            torch.cuda.empty_cache()

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                stag_ct = 0
            else:
                stag_ct += 1

            if stag_ct > cfg.trainer.patience or epoch == cfg.trainer.max_epochs - 1:
                if epoch >= cfg.trainer.min_epochs:
                    break

    except KeyboardInterrupt:
        print("\nTraining interrupted by user.")

    logger.close()

    # Clean up
    del model
    del optimizer
    del scheduler
    torch.cuda.empty_cache()

    return best_val_loss


def objective(trial: optuna.Trial) -> float:
    """Optuna objective function."""

    # Suggest hyperparameters
    batch_size = trial.suggest_categorical("batch_size", [16, 32, 64, 128])
    lr = trial.suggest_float("lr", 1e-5, 1e-3, log=True)
    weight_decay = trial.suggest_float("weight_decay", 1e-6, 1e-3, log=True)
    p_drop = trial.suggest_float("p_drop", 0.0, 0.5)

    # Initialize Hydra configuration
    with initialize(config_path="../../conf", version_base=None):
        cfg = compose(
            config_name="train_param",
            overrides=[
                f"data.batch_size={batch_size}",
                f"trainer.optimizer.lr={lr}",
                f"trainer.optimizer.weight_decay={weight_decay}",
                f"trainer.scheduler.patience=12",
                f"trainer.patience=24",
                f"model.p_drop={p_drop}",
                "debug=false",
            ],
        )

    # Train and get validation loss
    val_loss = train_with_config(cfg)

    return val_loss


def main():
    """Run Optuna hyperparameter search."""

    # Create study
    study = optuna.create_study(
        direction="minimize",
        study_name="hpo_param",
        storage=None,
        load_if_exists=True,
    )

    # Run optimization
    hours = 7
    study.optimize(objective, n_trials=4096, timeout=int(hours * 3600))

    # Print results
    print("\n" + "=" * 50)
    print("Best trial:")
    trial = study.best_trial
    print(f"  Value (validation loss): {trial.value}")
    print("  Params:")
    for key, value in trial.params.items():
        print(f"    {key}: {value}")

    # Save best hyperparameters
    best_params_path = "logs/best_hyperparameters_param.yaml"
    os.makedirs(os.path.dirname(best_params_path), exist_ok=True)

    best_config = OmegaConf.create(
        {
            "data": {"batch_size": trial.params["batch_size"]},
            "trainer": {
                "optimizer": {
                    "lr": trial.params["lr"],
                    "weight_decay": trial.params["weight_decay"],
                }
            },
        }
    )

    OmegaConf.save(best_config, best_params_path)
    print(f"\nBest hyperparameters saved to {best_params_path}")


if __name__ == "__main__":
    main()
