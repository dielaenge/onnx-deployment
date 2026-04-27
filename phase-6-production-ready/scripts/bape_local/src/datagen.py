import os
from pathlib import Path

import hydra
from hydra.utils import call
from omegaconf import DictConfig, OmegaConf


@hydra.main(config_path="../conf", config_name="datagen_rirs", version_base=None)
def main(cfg: DictConfig) -> None:

    if cfg.write_flag:
        out_path = Path(os.getcwd()) / cfg.out_path
        out_path.mkdir(parents=True, exist_ok=False)
        OmegaConf.save(config=cfg, f=out_path / "config.yaml")

    call(cfg)


if __name__ == "__main__":
    main()
