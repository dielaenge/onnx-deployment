from math import ceil
from pathlib import Path
from typing import Optional, Union

import torch
from torch import nn
from torch import Tensor
from omegaconf import OmegaConf, DictConfig, ListConfig
from hydra.utils import instantiate

from src.model.vae import VAE
from src.model.mlp import RegressionHead
from src.model.speech_encoder import SpeechEncoder


class ParameterEstimator(nn.Module):

    def __init__(
        self,
        encoder_state: Union[str, None],
        freeze_encoder: bool,
        reset_encoder: bool,
        quantiles: Optional[ListConfig[float]],
        estimator: DictConfig,
        p_drop: float = 0.3,
    ) -> None:
        super().__init__()

        self._freeze_encoder = freeze_encoder

        # try to load config.yaml in the log directory of the encoder state
        if encoder_state is not None:
            if Path(encoder_state).exists():
                config_path = Path(encoder_state).parent / "config.yaml"
                cfg = OmegaConf.load(config_path)
                self.encoder = instantiate(cfg.model)
                state = torch.load(encoder_state)
                self.encoder.load_state_dict(state, strict=True)
            else:
                raise FileNotFoundError(f"Encoder state not found: {encoder_state}")

        if encoder_state is None:
            config_path = Path("conf/model/speech_encoder.yaml")
            print(f"Using default config: {config_path}")
            cfg = OmegaConf.load(config_path)
            self.encoder = instantiate(cfg)

        if reset_encoder:
            print("Resetting encoder weights.")
            self.encoder.init_weights()

        if freeze_encoder:
            for param in self.encoder.parameters():
                param.requires_grad = False
            self.encoder.eval()

        if isinstance(self.encoder, VAE):
            self.is_vae = True
        elif isinstance(self.encoder, SpeechEncoder):
            self.is_vae = False
        else:
            raise ValueError("Encoder must be either VAE or SpeechEncoder.")

        # create regression heads
        if quantiles is None:
            self.num_heads = 1
            self.conformalize = False
            self.heads = nn.ModuleList([RegressionHead(**estimator)])
        else:
            self.conformalize = True
            self.num_heads = len(quantiles)
            self.heads = nn.ModuleList(
                [RegressionHead(**estimator) for _ in range(self.num_heads)]
            )
            # init conformal prediction adjustment
            self.register_buffer(
                "quantile_adjustment", torch.zeros(estimator.output_dim)
            )

        self.dropout = nn.Dropout(p_drop)

    def conformalize_quantiles(self, labels: Tensor, lower: Tensor, upper: Tensor):
        # separate conformal prediction for each sub band
        for i, (lo, hi, lab) in enumerate(zip(lower.T, upper.T, labels.T)):
            scores = torch.max(torch.stack([lo - lab, lab - hi], dim=1), dim=1)[0]
            n = scores.size(0)
            alpha = 0.1  # 10 % error rate
            q = ceil((n + 1) * (1 - alpha)) / n
            q_hat = torch.quantile(scores, q, interpolation="higher")
            self.quantile_adjustment[i] = q_hat

    def forward(self, x: Tensor) -> Tensor:
        if self._freeze_encoder:
            with torch.no_grad():
                if self.is_vae:
                    z = self.encoder.encode(x)[0].flatten(start_dim=1)
                else:
                    z = self.encoder(x)[0]
        else:
            if self.is_vae:
                z = self.encoder.encode(x)[0].flatten(start_dim=1)
            else:
                z = self.encoder(x)[0]

        z = self.dropout(z)

        output = torch.stack([head(z) for head in self.heads], dim=2)

        if self.conformalize:
            # compute conformalized predictions
            quantiles_adjusted = torch.stack(
                [
                    output[..., 0] - self.quantile_adjustment[None, :],
                    output[..., -1] + self.quantile_adjustment[None, :],
                ],
                dim=2,
            )
        else:
            quantiles_adjusted = None
        return output, quantiles_adjusted
