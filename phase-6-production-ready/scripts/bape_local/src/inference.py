import os
import pickle

import hydra
import torch
import torch.nn as nn
import torch.nn.functional as F
from tqdm import tqdm
from torch.utils.data import DataLoader
from hydra.utils import instantiate
from omegaconf import DictConfig, OmegaConf

from src.data.datamodule import DataModule
from src.data.wavdir import WaveDirectoryDataset
from src.util.utils import get_device, create_log_dir
from src.util.layers import count_trainable_parameters
from src.util.metrics import compute_regression_metrics


def step(model, batch, device):
    wetspec, fname = batch
    wetspec = wetspec.to(device)
    est = model(wetspec[None, ...])
    return {"est": est, "fname": fname}


@hydra.main(config_path="../conf", config_name="inference_param", version_base=None)
def main(cfg: DictConfig) -> None:

    device = get_device("cuda")

    # cudnn backend
    if torch.backends.cudnn.is_available():
        torch.backends.cudnn.benchmark = True

    log_dir, out_dir = create_log_dir(subdir="inference", debug=cfg.debug)

    # write config file to logdir
    OmegaConf.save(config=cfg, f=os.path.join(log_dir, "config.yaml"))

    # instantiate the model and data module
    data: DataModule = instantiate(cfg.data)

    if isinstance(data, DataModule):
        dloader = data.test_dataloader()
    elif isinstance(data, WaveDirectoryDataset):
        dloader = DataLoader(dataset=data, batch_size=1, num_workers=0, drop_last=False)
    else:
        raise ValueError("Data must be either DataModule or WaveDirectoryDataset.")

    # instantiate the model
    cfg.model.encoder_state = None
    model: nn.Module = instantiate(cfg.model)

    print(f"Model has {count_trainable_parameters(model):,} trainable parameters.")
    state = torch.load(cfg.state, map_location=device)
    model.load_state_dict(state, strict=True)

    # move models to device
    model.to(device)

    try:
        model.eval()
        batch_idx = 0
        outputs = []
        for batch in tqdm(dloader):
            with torch.no_grad():
                step_dict = step(model, batch, device)

                out_dict = {
                    "est": step_dict["est"].cpu(),
                    "fname": step_dict["fname"],
                }

                outputs.append(out_dict)
                batch_idx += 1
        # compute and save metrics
        compute_regression_metrics(outputs, out_dir)

        # write outputs
        with open(os.path.join(out_dir, "output.pkl"), "wb") as f:
            pickle.dump(outputs, f)

    except KeyboardInterrupt:
        print("\nTesting interrupted by user, no metrics computed.")

    print("Done.")


if __name__ == "__main__":
    main()
