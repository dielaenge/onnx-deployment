from typing import Union, Tuple, Optional
import math
import pickle
import torch
from torch import nn
from torch import Tensor
import torch.nn.functional as F
from einops import rearrange

from scripts.bape_local.src.model.cnn2d import CNNEncoder
from scripts.bape_local.src.model.mlp import DenseBlock
from scripts.bape_local.src.util.layers import SelfAttentionPooling
from scripts.bape_local.src.model.film import FiLMBlock


class SpeechEncoder(nn.Module):
    """
    SpeechEncoder combines a front-end CNN, a sequence model, and an optional error model.
    It supports conformal prediction interval adjustment and state loading.
    """

    def __init__(
        self,
        front_end: CNNEncoder,
        sequence_model: nn.Module,
        error_model: Optional[nn.Module] = None,
        state: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.front_end = front_end
        self.sequence_model = sequence_model
        self.error_model = error_model

        if self.error_model is not None:
            n_adjust = self.error_model.d_out // 2
            self.register_buffer("quantile_adjustment", torch.zeros(n_adjust))

        if state is not None:
            with open(state, "rb") as f:
                state_dict = pickle.load(f)
            self.load_state_dict(state_dict["component_state"])
            print(f"Transformer @ {hex(id(self))} state successfully loaded:\n{state}")

    def init_weights(self) -> None:
        """Recursively initialize all submodules."""
        self.apply(self._init_weights)

    def _init_weights(self, module: nn.Module) -> None:
        """Initialize weights of the model."""
        if isinstance(module, (nn.Linear, nn.Conv1d, nn.Conv2d)):
            nn.init.xavier_uniform_(module.weight)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        # init transformer layers
        elif isinstance(module, nn.MultiheadAttention):
            nn.init.xavier_uniform_(module.in_proj_weight)
            nn.init.xavier_uniform_(module.out_proj.weight)
            if module.in_proj_bias is not None:
                nn.init.zeros_(module.in_proj_bias)
            if module.out_proj.bias is not None:
                nn.init.zeros_(module.out_proj.bias)
        elif isinstance(module, nn.LayerNorm):
            nn.init.ones_(module.weight)
            nn.init.zeros_(module.bias)

    def forward(
        self, x: Tensor
    ) -> Tuple[Tensor, Tensor, Optional[Tensor], Optional[Tensor]]:
        """
        Forward pass through the encoder.
        Returns:
            latent: Latent features
            latent_weights: Attention or pooling weights
            quantiles: (optional) Quantile predictions if error_model is present
            quantiles_adjusted: (optional) Adjusted quantiles if error_model is present
        """
        tokens = self.front_end(x)
        tokens = rearrange(tokens, "b c f t -> b t (c f)")
        latent, latent_weights = self.sequence_model(tokens)

        if self.error_model is not None:
            quantiles, _ = self.error_model(tokens.detach(), latent.detach())
            num_bands = quantiles.size(1) // 2
            quantiles = quantiles.view(quantiles.size(0), num_bands, 2)
            quantiles_adjusted = [
                torch.clamp(quantiles[..., 0] - self.quantile_adjustment, min=0),
                quantiles[..., -1] + self.quantile_adjustment,
            ]
            quantiles_adjusted = torch.stack(quantiles_adjusted, dim=-1)
            return latent, latent_weights, quantiles, quantiles_adjusted

        return latent, latent_weights, None, None

    @torch.no_grad()
    def conformalize_quantiles(
        self, errors: Tensor, lower: Tensor, upper: Tensor
    ) -> None:
        """
        Adjust quantile intervals using conformal prediction.
        """
        offsets = torch.stack([lower - errors, errors - upper], dim=-1)
        scores = torch.max(offsets, dim=-1)[0]
        n = scores.size(0)
        alpha = 0.1
        q = math.ceil((n + 1) * (1 - alpha)) / n
        q_hat = torch.quantile(scores, q, interpolation="higher", dim=0)
        self.quantile_adjustment = q_hat
