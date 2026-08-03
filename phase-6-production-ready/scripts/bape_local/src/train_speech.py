import os
import pickle
from collections import deque

import hydra
import torch
import torch.nn as nn
from tqdm import tqdm
from hydra.utils import instantiate
from torch.utils.tensorboard import SummaryWriter
from omegaconf import DictConfig, OmegaConf
from fvcore.nn import FlopCountAnalysis, parameter_count

from src.data.datamodule import DataModule
from src.util.utils import get_device, create_log_dir
from src.util.layers import count_trainable_parameters
from src.util.loss import kld_gaussian_diag, quantile_loss
from src.util.plot_utils import speech_encoder_output

# Set sharing strategy to avoid "Too many open files" error with DataLoader workers
torch.multiprocessing.set_sharing_strategy("file_system")


def step(model, rir_encoder, batch, device):
    wetspec, rirspec, norm, snr, param = batch
    rirspec = rirspec.to(device)
    wetspec = wetspec.to(device)

    # get variational rir posterior
    zh, vardict = rir_encoder.encode(rirspec)
    mu_h = vardict["variational_mean"].flatten(start_dim=1)
    # called "variational_std" but its actually the log-variance
    var_h = torch.exp(vardict["variational_std"]).flatten(start_dim=1)

    # approximated means, attention weights, quantiles, and conformal quantiles
    mu_y, w_mu, q, qc = model(wetspec)
    latent_loss = kld_gaussian_diag(mu_y, mu_h, var_h)
    # latent_loss = torch.mean((mu_y - mu_h) ** 2)

    # run error model
    rirspec_hat = rir_encoder.decode(mu_y.view(zh.shape))
    scale, shift = norm["rirspec_std"].to(device), norm["rirspec_mean"].to(device)
    rirspec_hat = rirspec_hat * scale[:, None, None, None] + shift[:, None, None, None]
    rirspec = rirspec * scale[:, None, None, None] + shift[:, None, None, None]

    errors = torch.mean(torch.abs(rirspec_hat - rirspec), dim=-1).squeeze()
    error_loss = quantile_loss(q, errors, quantiles=[0.05, 0.95])

    return {
        "latent_loss": latent_loss,
        "error_loss": error_loss,
        "errors": errors,
        "rirspec": rirspec,
        "rirspec_hat": rirspec_hat,
        "quantiles": q,
        "quantiles_conformal": qc,
        "norm": norm,
        "param": param,
        "snr": snr,
    }


@hydra.main(
    config_path="../conf", config_name="train_speech_encoder", version_base=None
)
def main(cfg: DictConfig) -> None:

    device = get_device("cuda")

    # cudnn backend
    if torch.backends.cudnn.is_available():
        torch.backends.cudnn.benchmark = True

    log_dir, out_dir = create_log_dir(subdir="speech_encoder", debug=cfg.debug)

    # write config file to logdir
    OmegaConf.save(config=cfg, f=os.path.join(log_dir, "config.yaml"))

    # instantiate the model and data module
    data: DataModule = instantiate(cfg.data)
    model: nn.Module = instantiate(cfg.model)

    print(f"Model has {count_trainable_parameters(model):,} trainable parameters.")

    # Print trainable parameters for each component
    front_end_params = sum(
        p.numel() for p in model.front_end.parameters() if p.requires_grad
    )
    print(f"  Front-end trainable parameters: {front_end_params:,}")

    sequence_params = sum(
        p.numel() for p in model.sequence_model.parameters() if p.requires_grad
    )
    print(f"  Sequence model trainable parameters: {sequence_params:,}")

    error_params = sum(
        p.numel() for p in model.error_model.parameters() if p.requires_grad
    )
    print(f"  Error model trainable parameters: {error_params:,}")

    # instantiate optimizer and scheduler
    optimizer = instantiate(cfg.trainer.optimizer, params=model.parameters())
    scheduler = (
        instantiate(cfg.trainer.scheduler, optimizer=optimizer)
        if cfg.trainer.scheduler is not None
        else None
    )

    # instantiate rir_enoder
    rir_encoder = instantiate(cfg.rir_encoder)
    rir_encoder.eval()

    # move models to device
    model.to(device)
    rir_encoder.to(device)

    # logging and early stopping stuff
    logger = SummaryWriter(log_dir)
    step_idx, stag_ct, best_val_loss = 0, 0, 1e10
    best_state = model.state_dict()

    # init calibration set for conformal prediction
    calibration_set = deque()

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
                    step_dict = step(model, rir_encoder, batch, device)
                    loss = step_dict["latent_loss"] + step_dict["error_loss"]
                    loss.backward()
                    optimizer.step()
                    logger.add_scalar(
                        "loss/train_latent", step_dict["latent_loss"].item(), step_idx
                    )
                    logger.add_scalar(
                        "loss/train_error", step_dict["error_loss"].item(), step_idx
                    )
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
                        step_dict = step(model, rir_encoder, batch, device)
                        loss = step_dict["latent_loss"] + step_dict["error_loss"]

                        calibration_set.append(
                            {
                                "errors": step_dict["errors"],
                                "quantiles": step_dict["quantiles"],
                            }
                        )

                        val_loss += loss.item()
                        batch_idx += 1
                # average validation loss
                val_loss /= batch_idx
                logger.add_scalar("loss/valid_epoch", val_loss, step_idx)

                # conformalize quantiles
                errors = torch.cat([batch["errors"] for batch in calibration_set])
                lower = torch.cat(
                    [batch["quantiles"][..., 0] for batch in calibration_set]
                )
                upper = torch.cat(
                    [batch["quantiles"][..., -1] for batch in calibration_set]
                )
                model.conformalize_quantiles(errors, lower, upper)
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
        epoch_loss, batch_idx = 0, 0
        outputs = []
        for batch in tqdm(data.test_loader):
            with torch.no_grad():
                step_dict = step(model, rir_encoder, batch, device)
                out_dict = {
                    "rirspec": step_dict["rirspec"].cpu(),
                    "rirspec_hat": step_dict["rirspec_hat"].cpu(),
                    "errors": step_dict["errors"].cpu(),
                    "quantiles": step_dict["quantiles"].cpu(),
                    "quantiles_conformal": step_dict["quantiles_conformal"].cpu(),
                    "norm": step_dict["norm"],
                    "param": step_dict["param"],
                    "snr": step_dict["snr"],
                }
                outputs.append(out_dict)
                loss = step_dict["latent_loss"] + step_dict["error_loss"]
                epoch_loss += loss.item()
                batch_idx += 1

        epoch_loss /= batch_idx
        logger.add_scalar("loss/test", epoch_loss)
        print(f"Test loss: {epoch_loss}")

        # complexity analysis
        wetspec = batch[0]
        sample_input = wetspec[:1].to(device)
        flops = FlopCountAnalysis(model, sample_input)
        total_flops = flops.total()
        total_params = parameter_count(model)[""]

        print(f"FLOPs: {total_flops / 1e9:.2f} GFLOPs")
        print(f"Parameters: {total_params / 1e6:.2f} M")

        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats(device)
        with torch.no_grad():
            _ = model(sample_input)
        memory_allocated = torch.cuda.max_memory_allocated(device) / (1024**2)
        print(f"Peak memory usage: {memory_allocated:.2f} MB")

        with open(os.path.join(log_dir, "complexity.txt"), "w") as f:
            f.write(f"FLOPs: {total_flops / 1e9:.2f} GFLOPs\n")
            f.write(f"Parameters: {total_params / 1e6:.2f} M\n")
            f.write(f"Peak memory usage: {memory_allocated:.2f} MB\n")

        # generate plots
        print("Generating output plots...")
        speech_encoder_output(outputs=outputs, path=out_dir, num=32)

        # write outputs
        with open(os.path.join(out_dir, "outputs.pkl"), "wb") as f:
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
