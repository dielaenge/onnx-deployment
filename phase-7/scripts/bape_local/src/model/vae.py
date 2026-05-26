import pickle
from typing import Optional

import torch
from einops import rearrange
from torch import Tensor
from torch import nn
from omegaconf import ListConfig
from scripts.bape_local.src.util.layers import VariationalBottleneck
from scripts.bape_local.src.model.cnn2d import CNNEncoder, CNNDecoder


class VAE(nn.Module):
    """Variational autoencoder for RIRs"""

    def __init__(
        self,
        in_channels: int,
        channels: int,
        multipliers: ListConfig,
        kernel_sizes: ListConfig,
        strides: ListConfig,
        factors: ListConfig,
        pads: ListConfig,
        num_blocks: ListConfig,
        kl_weight: float,
        latent_proj: int,
        quantizer: Optional[nn.Module] = None,
        state: str | None = None,
    ) -> None:
        super().__init__()

        # compute dimensions
        self.out_channels = channels * multipliers[-1]
        self.kl_weight = kl_weight
        self.latent_proj = latent_proj

        # quantizer module
        if quantizer is None:
            self.quantizer = nn.Identity()
        elif quantizer is not None:
            self.quantizer = quantizer

        # store state path
        self.state = state

        z_dim = latent_proj if latent_proj is not None else self.out_channels

        # encoder consists of cnn and variational bottleneck
        self.encoder = CNNEncoder(
            in_channels=in_channels,
            channels=channels,
            multipliers=multipliers,
            factors=factors,
            num_blocks=num_blocks,
            kernel_sizes=kernel_sizes,
            strides=strides,
            pads=pads,
            resnet_groups=8,
            latent_proj=latent_proj,
        )

        self.bneck = VariationalBottleneck(
            channels=z_dim,
            loss_weight=kl_weight,
        )

        # decoder
        self.decoder = CNNDecoder(
            out_channels=in_channels,
            channels=channels,
            multipliers=multipliers[::-1],
            factors=factors[::-1],
            num_blocks=num_blocks[::-1],
            kernel_sizes=kernel_sizes[::-1],
            strides=strides[::-1],
            pads=pads[::-1],
            latent_proj=latent_proj,
            resnet_groups=8,
        )

        if state is not None:
            state_dict = torch.load(state)
            self.load_state_dict(state_dict)
            # self.decoder.load_state_dict(state_dict["decoder_state"])
            print(f"RIR-VAE @ {hex(id(self))} state succesfully loaded:\n{state}")

    def forward(self, x: Tensor) -> Tensor:
        x = self.encoder(x)
        _, _, f, t = x.size()
        x = rearrange(x, "b c f t -> b c (f t)")
        z, var_dict = self.bneck(x, with_info=True)
        z = rearrange(z, "b c (f t) -> b c f t", f=f, t=t)
        z = self.quantizer(z)
        y = self.decoder(z)
        return y, z, var_dict

    @torch.no_grad()
    def encode(self, x: Tensor) -> Tensor:
        x = self.encoder(x)
        _, _, f, t = x.size()
        x = rearrange(x, "b c f t -> b c (f t)")
        z, var_dict = self.bneck(x, with_info=True)
        z = rearrange(z, "b c (f t) -> b c f t", f=f, t=t)
        z = self.quantizer(z)
        return z, var_dict

    @torch.no_grad()
    def decode(self, z: Tensor) -> Tensor:
        return self.decoder(z)

    def count_trainable_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
