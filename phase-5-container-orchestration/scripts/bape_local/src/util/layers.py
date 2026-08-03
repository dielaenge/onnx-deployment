from typing import Tuple, Union, Any

import torch
import torch.nn as nn
import torch.nn.functional as F
from einops import reduce
from torch import Tensor


def reset_transformer_weights(module: nn.Module) -> None:
    if hasattr(module, "reset_parameters"):
        module.reset_parameters()  # If the submodule has reset_parameters, use it


def weights_init(module: nn.Module) -> None:
    if (
        isinstance(module, nn.Conv1d)
        or isinstance(module, nn.Conv2d)
        or isinstance(module, nn.Conv3d)
        or isinstance(module, nn.Linear)
        or isinstance(module, nn.LSTM)
        or isinstance(module, nn.GRU)
        # or isinstance(module, nn.TransformerEncoder)
    ):
        module.reset_parameters()

    if isinstance(module, nn.TransformerEncoderLayer):
        module.apply(reset_transformer_weights)


class PermuteLayer(nn.Module):
    """Layer for rearranging tensor dims as element in nn.Sequential"""

    def __init__(self, dims: tuple) -> None:
        super().__init__()
        self.dims = dims

    def forward(self, tensor: Tensor) -> Tensor:
        return tensor.permute(*self.dims).contiguous()


class LeTanh(nn.Module):
    """Yann LeCun's hyperbolic tangent activation"""

    def __init__(self) -> None:
        super().__init__()

    def forward(self, tensor: Tensor) -> Tensor:
        return 1.7159 * torch.tanh(2 / 3 * tensor)


class ReLU_plus(nn.Module):
    """ReLU plus fixed offset"""

    def __init__(self, offset: float = 0.0) -> None:
        super().__init__()
        self.offset = torch.tensor(offset, dtype=torch.float32)

    def forward(self, tensor: Tensor) -> Tensor:
        return F.relu(tensor) + self.offset


class LPNormalization(nn.Module):
    """ "Wrapper for feature normalization"""

    def __init__(self, order: float = 2.0, dim: int = -1) -> None:
        super().__init__()
        self.order = order
        self.dim = dim

    def forward(self, tensor: Tensor) -> Tensor:
        # Assumes B x E
        return F.normalize(tensor, p=self.order, dim=self.dim)


class SelfAttentionPooling(nn.Module):
    # """
    # Implementation of SelfAttentionPooling
    # Original Paper: Self-Attention Encoding and Pooling for Speaker Recognition
    # https://arxiv.org/pdf/2008.01077v1.pdf
    # """

    def __init__(self, d_model, num_hidden_layers: int = 0) -> None:
        super().__init__()
        assert num_hidden_layers >= 0
        self.W = nn.Sequential()
        for _ in range(num_hidden_layers):
            self.W.append(nn.Linear(in_features=d_model, out_features=d_model))
            self.W.append(nn.Tanh())
        self.W.append(nn.Linear(in_features=d_model, out_features=1, bias=False))

    def forward(self, tensor: Tensor) -> Tuple[Tensor, Tensor]:
        logits = self.W(tensor).squeeze(-1)
        weights = F.softmax(logits, dim=1).unsqueeze(-1)
        pooled = torch.sum(tensor * weights, dim=1)
        return pooled, weights


def count_trainable_parameters(module: nn.Module) -> int:
    """Counts the number of trainable parameters in a nn.Module."""
    return sum(p.numel() for p in module.parameters() if p.requires_grad)


"""Variational Bottleneck modified version from
https://github.com/archinetai/audio-encoders-pytorch/blob/main/audio_encoders_pytorch/modules.py
"""


def gaussian_sample(mean: Tensor, logvar: Tensor) -> Tensor:
    std = torch.exp(0.5 * logvar)
    eps = torch.randn_like(std)
    sample = mean + std * eps
    return sample


def kl_loss(mean: Tensor, logvar: Tensor) -> Tensor:
    losses = mean**2 + logvar.exp() - logvar - 1
    loss = reduce(losses, "b ... -> 1", "mean")
    return loss


class VariationalBottleneck(nn.Module):
    def __init__(self, channels: int, loss_weight: float = 1.0):
        super().__init__()
        self.loss_weight = loss_weight
        self.to_mean_and_std = nn.Conv1d(
            in_channels=channels,
            out_channels=channels * 2,
            kernel_size=1,
        )

    def forward(
        self, x: Tensor, with_info: bool = False
    ) -> Union[Tensor, Tuple[Tensor, Any]]:
        mean_and_std = self.to_mean_and_std(x)
        mean, std = mean_and_std.chunk(chunks=2, dim=1)
        mean = torch.tanh(mean)  # mean in range [-1, 1]
        std = torch.tanh(std) + 1.0  # std in range [0, 2]
        out = gaussian_sample(mean, std)
        info = dict(
            variational_kl_loss=kl_loss(mean, std) * self.loss_weight,
            variational_mean=mean,
            variational_std=std,
        )
        return (out, info) if with_info else out
