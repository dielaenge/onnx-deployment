from typing import Any
import torch
from torch import Tensor
import torch.nn as nn
import torch.nn.functional as F


def apply_fourier_features(x: Tensor, B: Tensor) -> Tensor:
    projection = (2 * torch.pi * x) @ B.to(x)
    transformed = torch.cat([torch.sin(projection), torch.cos(projection)], dim=-1)
    return transformed


class LatentModulator(nn.Module):
    """Model for learning a parametric latent mapping"""

    def __init__(
        self,
        latent_dim: int,
        param_dim: int,
        num_blocks: int,
    ) -> None:
        super().__init__()

        self.modulator = nn.Sequential()

        for _ in range(num_blocks):
            self.modulator.append(
                FiLMBlock(
                    num_features=latent_dim,
                    latent_size=param_dim,
                )
            )

    def forward(self, latent: Tensor, params: Tensor) -> Tensor:
        for block in self.modulator:
            latent = block(x=latent, z=params)
        return latent


class FiLMBlock(nn.Module):
    "Feature-wise linear modulation layer"

    def __init__(self, num_features: int, latent_size: int) -> None:
        super().__init__()
        self.num_features = num_features
        self.latent_size = latent_size

        self.beta = nn.Linear(latent_size, num_features)
        self.gamma = nn.Linear(latent_size, num_features)
        # self.affine = nn.Linear(num_features, num_features)

        self.norm = nn.LayerNorm(normalized_shape=(num_features,))

    def forward(self, x: Tensor, z: Tensor) -> Tensor:
        beta = self.beta(z)
        gamma = self.gamma(z)
        # return self.norm(self.affine(x) * gamma + beta)
        return self.norm(x * gamma + beta)
