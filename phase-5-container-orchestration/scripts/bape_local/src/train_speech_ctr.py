import os
import pickle

import hydra
import torch
import torch.nn as nn
from tqdm import tqdm
from hydra.utils import instantiate
from torch.utils.tensorboard import SummaryWriter
from omegaconf import DictConfig, OmegaConf

from src.data.datamodule import DataModule
from src.util.utils import get_device, create_log_dir
from src.util.layers import count_trainable_parameters
from src.util.loss import MultiPosConLoss


def step(model, adapter, batch, device):
    signal, rir_idxs, norm, snr = batch
    signal = signal.to(device)
    rir_idxs = rir_idxs.to(device)
    signal = signal.squeeze(0)

    z, w_z, _, _ = model(signal)
    zz = adapter(z)

    return {
        "z": z,
        "w_z": w_z,
        "zz": zz,
        "rir_idxs": rir_idxs,
    }


@hydra.main(
    config_path="../conf", config_name="train_speech_encoder_ctr", version_base=None
)
def main(cfg: DictConfig) -> None:

    device = get_device("cuda")

    # cudnn backend
    if torch.backends.cudnn.is_available():
        torch.backends.cudnn.benchmark = True

    log_dir, out_dir = create_log_dir(subdir="ctr", debug=cfg.debug)

    # write config file to logdir
    OmegaConf.save(config=cfg, f=os.path.join(log_dir, "config.yaml"))

    # instantiate the model and data module
    data: DataModule = instantiate(cfg.data)
    model: nn.Module = instantiate(cfg.model)
    adapter: nn.Module = instantiate(cfg.adapter)

    print(f"Model has {count_trainable_parameters(model):,} trainable parameters.")

    # instantiate optimizer and scheduler
    optimizer = instantiate(
        cfg.trainer.optimizer,
        params=list(model.parameters()) + list(adapter.parameters()),
    )
    scheduler = (
        instantiate(cfg.trainer.scheduler, optimizer=optimizer)
        if cfg.trainer.scheduler is not None
        else None
    )

    # move models to device
    model.to(device)
    adapter.to(device)

    closs = MultiPosConLoss(temperature=cfg.trainer.temperature).to(device)

    # logging and early stopping stuff
    logger = SummaryWriter(log_dir)
    step_idx, stag_ct, best_val_loss = 0, 0, 1e10
    best_model, best_adpter = model.state_dict(), adapter.state_dict()

    # catch keyboard interrupts
    try:
        for epoch in range(cfg.trainer.max_epochs):

            logger.add_scalar("epoch", epoch, step_idx)
            batch_idx, train_loss = 0, 0
            model.train(), adapter.train()

            with tqdm(
                data.train_loader,
                desc=f"Epoch {epoch + 1}/{cfg.trainer.max_epochs}",
                leave=False,
            ) as pbar:

                # training loop
                for batch in pbar:
                    optimizer.zero_grad()
                    step_dict = step(model, adapter, batch, device)
                    feats = step_dict["zz"]
                    labels = step_dict["rir_idxs"]
                    loss = closs(feats, labels)
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
                        optimizer.zero_grad()
                        step_dict = step(model, adapter, batch, device)
                        feats = step_dict["zz"]
                        labels = step_dict["rir_idxs"]
                        loss = closs(feats, labels)

                        val_loss += loss.item()
                        batch_idx += 1

                # average validation loss
                val_loss /= batch_idx
                logger.add_scalar("loss/valid_epoch", val_loss, step_idx)

            # update scheduler
            if scheduler is not None:
                scheduler.step(val_loss)

            torch.cuda.empty_cache()
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_model = model.state_dict()
                best_adpter = adapter.state_dict()
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

    # load the best states
    model.load_state_dict(best_model)
    adapter.load_state_dict(best_adpter)

    try:
        epoch_loss, batch_idx, outputs = 0, 0, []
        for batch in tqdm(data.test_loader):
            with torch.no_grad():
                optimizer.zero_grad()
                step_dict = step(model, adapter, batch, device)
                feats = step_dict["zz"]
                labels = step_dict["rir_idxs"]
                loss = closs(feats, labels)

                out_dict = {
                    "rir_idxs": step_dict["rir_idxs"].cpu(),
                    "z": step_dict["z"].cpu(),
                    "zz": step_dict["zz"].cpu(),
                    # "params": step_dict["params"],
                }

                outputs.append(out_dict)

                epoch_loss += loss.item()
                batch_idx += 1

        epoch_loss /= batch_idx
        logger.add_scalar("loss/test", epoch_loss)
        print(f"Test loss: {epoch_loss}")
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
