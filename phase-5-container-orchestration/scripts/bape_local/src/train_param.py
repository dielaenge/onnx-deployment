import os
import pickle
from collections import deque

import hydra
import torch
import torch.nn as nn
import torch.nn.functional as F
from tqdm import tqdm
from hydra.utils import instantiate
from torch.utils.tensorboard import SummaryWriter
from omegaconf import DictConfig, OmegaConf

from src.data.datamodule import DataModule
from src.util.utils import get_device, create_log_dir
from src.util.layers import count_trainable_parameters
from src.util.metrics import compute_regression_metrics
from src.util.loss import quantile_loss


def step(model, batch, target, device):
    wetspec, _, _, snr, param = batch

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


@hydra.main(config_path="../conf", config_name="train_param", version_base=None)
def main(cfg: DictConfig) -> None:

    device = get_device("cuda")

    # cudnn backend
    if torch.backends.cudnn.is_available():
        torch.backends.cudnn.benchmark = True

    subdir = cfg.subdir if cfg.subdir is not None else "param"
    log_dir, _ = create_log_dir(subdir=subdir, debug=cfg.debug)

    # write config file to logdir
    OmegaConf.save(config=cfg, f=os.path.join(log_dir, "config.yaml"))

    # instantiate the model and data module
    data: DataModule = instantiate(cfg.data)
    model: nn.Module = instantiate(cfg.model)

    print(f"Model has {count_trainable_parameters(model):,} trainable parameters.")

    # create parameter groups with different learning rates
    encoder_params = []
    head_params = []

    for name, param in model.named_parameters():
        if (
            "encoder" in name.lower()
        ):  # adjust this condition based on your model structure
            encoder_params.append(param)
        else:
            head_params.append(param)

    param_groups = [
        {"params": encoder_params, "lr": cfg.trainer.encoder_lr},
        {"params": head_params, "lr": cfg.trainer.head_lr},
    ]

    # instantiate optimizer and scheduler
    optimizer_partial = instantiate(cfg.trainer.optimizer, _partial_=True)
    optimizer = optimizer_partial(params=param_groups)
    scheduler = (
        instantiate(cfg.trainer.scheduler, optimizer=optimizer)
        if cfg.trainer.scheduler is not None
        else None
    )

    # move models to device
    model.to(device)

    # logging and early stopping stuff
    logger = SummaryWriter(log_dir)
    step_idx, stag_ct, best_val_loss = 0, 0, 1e10
    best_state = model.state_dict()

    # init calibration set for conformal prediction
    calibration_set = deque()

    # target parameter
    target = cfg.target

    # catch keyboard interrupts
    try:
        for epoch in range(cfg.trainer.max_epochs):

            logger.add_scalar("epoch", epoch, step_idx)

            batch_idx, train_loss = 0, 0
            model.train()
            with tqdm(
                data.train_loader,
                desc=f"Epoch {epoch + 1}/{cfg.trainer.max_epochs}",
                leave=False,
            ) as pbar:

                # training loop
                for batch in pbar:
                    optimizer.zero_grad()
                    step_dict = step(model, batch, target, device)
                    loss = step_dict["loss"]
                    loss.backward()
                    optimizer.step()
                    logger.add_scalar("loss/train", loss.item(), step_idx)

                    train_loss += loss.item()
                    step_idx += 1
                    batch_idx += 1

                # average training loss
                train_loss /= batch_idx
                logger.add_scalar("loss/train_epoch", train_loss, step_idx)

                # validation loop
                model.eval()
                batch_idx, val_loss = 0, 0
                pbar.set_description("Validating...")
                pbar.refresh()
                for batch in data.valid_loader:
                    with torch.no_grad():
                        step_dict = step(model, batch, target, device)
                        loss = step_dict["loss"]
                        logger.add_scalar("loss/valid", loss.item(), step_idx)

                        # gather calbration set for conformal prediction
                        calibration_set.append(
                            {"gt": step_dict["gt"], "quant": step_dict["quant"]}
                        )

                        val_loss += loss.item()
                        batch_idx += 1
                # average validation loss
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
                best_state = model.state_dict()
                stag_ct = 0
            else:
                stag_ct += 1

            if (
                stag_ct > cfg.trainer.patience or epoch == cfg.trainer.max_epochs - 1
            ) and epoch >= cfg.trainer.min_epochs:
                print(f"Stopping after epoch {epoch}.")
                break

    except KeyboardInterrupt:
        print("\nTraining interrupted by user. Proceeding to testing...")

    # load the best model state
    model.load_state_dict(best_state)

    try:
        model.eval()
        epoch_loss, batch_idx = 0, 0
        outputs = []
        for batch in tqdm(data.test_loader):
            with torch.no_grad():
                step_dict = step(model, batch, target, device)
                loss = step_dict["loss"]

                step_dict["est"]

                out_dict = {
                    "est": step_dict["est"][..., 1].cpu(),
                    "gt": step_dict["gt"].cpu(),
                    "quant": step_dict["quant"].cpu(),
                    "quant_conf": step_dict["quant_conf"].cpu(),
                    "snr": step_dict["snr"],
                    "param": step_dict["param"],
                }

                outputs.append(out_dict)
                epoch_loss += loss.item()
                batch_idx += 1

        epoch_loss /= batch_idx
        logger.add_scalar("loss/test", epoch_loss)
        print(f"Test loss: {epoch_loss}")

        # compute and save metrics
        compute_regression_metrics(outputs, log_dir)

        # write outputs
        with open(os.path.join(log_dir, "output.pkl"), "wb") as f:
            pickle.dump(outputs, f)

    except KeyboardInterrupt:
        print("\nTesting interrupted by user, no metrics computed.")

    # save the model state
    model_path = os.path.join(log_dir, "model.pth")
    torch.save(model.cpu().state_dict(), model_path)
    print(f"Model saved to {model_path}")

    logger.close()


if __name__ == "__main__":
    main()
