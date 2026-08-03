import os
import pickle

import hydra
import torch
from tqdm import tqdm
from hydra.utils import instantiate
from torch.utils.tensorboard import SummaryWriter
from omegaconf import DictConfig, OmegaConf
import torch.nn.functional as F

from src.data.datamodule import DataModule
from src.model.vae import VAE
from src.util.utils import get_device, create_log_dir
from src.util.layers import count_trainable_parameters

# from src.util.loss import vae_reconstruction_loss
from src.util.plot_utils import vae_output


def step(model, batch, device):

    rir, spec, norm, _ = batch

    rir = rir.to(device)
    spec = spec.to(device)

    # send all tensors in norm to device
    for key in norm:
        if isinstance(norm[key], torch.Tensor):
            norm[key] = norm[key].to(device)

    recon, latent, var_dict = model(spec)

    return {
        "kl_loss": var_dict["variational_kl_loss"],
        "spec": spec,
        "rir": rir,
        "recon": recon,
        "latent": latent,
        "norm": norm,
    }


@hydra.main(config_path="../conf", config_name="train_rir_encoder", version_base=None)
def main(cfg: DictConfig) -> None:
    """
    Main training script for the FeedbackDelayNetwork model using Hydra for configuration management.
    """

    device = get_device("cuda")

    # cudnn backend
    if torch.backends.cudnn.is_available():
        torch.backends.cudnn.benchmark = True

    log_dir, out_dir = create_log_dir(subdir="vae", debug=cfg.debug)

    # write config file to logdir
    OmegaConf.save(config=cfg, f=os.path.join(log_dir, "config.yaml"))

    # instantiate the model and data module
    data: DataModule = instantiate(cfg.data)
    model: VAE = instantiate(cfg.model)

    print(f"Model has {count_trainable_parameters(model):,} trainable parameters.")

    # instantiate optimizer and scheduler
    optimizer = instantiate(cfg.trainer.optimizer, params=model.parameters())
    scheduler = (
        instantiate(cfg.trainer.scheduler, optimizer=optimizer)
        if cfg.trainer.scheduler is not None
        else None
    )

    # move model to device
    model.to(device)

    # tensorboard logging and early stopping stuff
    logger = SummaryWriter(log_dir)
    step_idx, stag_ct, best_val_loss = 0, 0, 1e10
    best_state = model.state_dict()

    try:
        for epoch in range(cfg.trainer.max_epochs):

            logger.add_scalar("epoch", epoch, step_idx)

            # training loop
            batch_idx, train_loss = 0, 0
            model.train()
            with tqdm(
                data.train_loader,
                desc=f"Epoch {epoch + 1}/{cfg.trainer.max_epochs}",
                leave=False,
            ) as pbar:
                for batch in pbar:
                    optimizer.zero_grad()
                    step_dict = step(model, batch, device)

                    kl_loss = step_dict["kl_loss"]
                    recon_loss = F.mse_loss(step_dict["recon"], step_dict["spec"])
                    loss = recon_loss + kl_loss * model.kl_weight

                    loss.backward()
                    optimizer.step()

                    logger.add_scalar("loss/train", loss.item(), step_idx)
                    logger.add_scalar("loss/train_recon", recon_loss.item(), step_idx)
                    logger.add_scalar("loss/train_kl", kl_loss.item(), step_idx)

                    train_loss += loss.item()
                    step_idx += 1
                    batch_idx += 1

                train_loss /= batch_idx
                logger.add_scalar("loss/train_epoch", train_loss, step_idx)

                # validation loop
                model.eval()
                batch_idx, val_loss = 0, 0
                pbar.set_description("Validating...")
                pbar.refresh()
                for batch in data.valid_loader:
                    with torch.no_grad():
                        step_dict = step(model, batch, device)

                        kl_loss = step_dict["kl_loss"]
                        recon_loss = F.mse_loss(step_dict["recon"], step_dict["spec"])
                        loss = recon_loss + kl_loss * model.kl_weight

                        val_loss += loss.item()
                        batch_idx += 1
                val_loss /= batch_idx
                logger.add_scalar("loss/valid_epoch", val_loss, step_idx)

            # update scheduler
            if scheduler is not None:
                scheduler.step(val_loss)

            # handle early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = model.state_dict()
                best_epoch = epoch
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
        best_epoch = epoch

    # load the best model state
    print(f"Loading best model state from epoch {best_epoch}.")
    print(f"Best validation loss: {best_val_loss}")
    model.load_state_dict(best_state)

    try:
        epoch_loss, batch_idx = 0, 0
        outputs = []
        for batch in data.test_loader:
            with torch.no_grad():
                step_dict = step(model, batch, device)

                kl_loss = step_dict["kl_loss"]
                recon_loss = F.mse_loss(step_dict["recon"], step_dict["spec"])
                loss = recon_loss + kl_loss * model.kl_weight

                # move all tensors in norm to CPU
                for key in step_dict["norm"]:
                    if isinstance(step_dict["norm"][key], torch.Tensor):
                        step_dict["norm"][key] = step_dict["norm"][key].cpu()

                out_dict = {
                    "rir": batch[0].cpu().numpy(),
                    "spec": batch[1].cpu().numpy(),
                    "recon": step_dict["recon"].cpu().numpy(),
                    "latent": step_dict["latent"].cpu().numpy(),
                    "norm": step_dict["norm"],
                }
                outputs.append(out_dict)
                epoch_loss += loss.item()
                batch_idx += 1
        epoch_loss /= batch_idx
        logger.add_scalar("loss/test_epoch", epoch_loss, step_idx)
        print(f"Test loss: {epoch_loss}")
        # generate plots
        print("Generating output plots...")
        vae_output(outputs=outputs, path=out_dir, num=32)
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
