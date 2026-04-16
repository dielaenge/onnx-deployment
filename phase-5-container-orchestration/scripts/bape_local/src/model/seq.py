from typing import Optional
import math
import torch
from torch import nn
from torch import Tensor

from scripts.bape_local.src.model.mlp import DenseBlock
from scripts.bape_local.src.util.layers import SelfAttentionPooling


class PositionalEncoding(nn.Module):
    """Taken from https://pytorch.org/tutorials/beginner/transformer_tutorial.html"""

    def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 5000):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model)
        )
        pe = torch.zeros(1, max_len, d_model)
        pe[0, :, 0::2] = torch.sin(position * div_term)
        pe[0, :, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe)

    def forward(self, x: Tensor) -> Tensor:
        """
        Arguments:
            x: Tensor, shape ``[batch_size, seq_len, embedding_dim]``
        """
        x = x + self.pe[:, : x.size(1), :]
        return self.dropout(x)


class SequenceModel(nn.Module):
    """Sequence model consisting of transformer encoder and sequence pooling"""

    def __init__(
        self,
        d_model: int,
        nhead: int,
        dim_feedforward: int,
        num_layers: int,
        dropout: float,
        d_out: int | None = None,
        act_out: str = "relu",
        att_pool: bool = True,
        film: Optional[nn.Module] = None,
    ) -> None:
        super().__init__()

        self.d_model = d_model
        self.nhead = nhead
        self.dim_forward = dim_feedforward
        self.num_layers = num_layers
        self.dropout = dropout
        self.d_out = d_out
        self.act_out = act_out
        self.att_pool = att_pool

        self.pe = PositionalEncoding(d_model=d_model, dropout=dropout)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            norm_first=False,
            activation="gelu",
        )

        self.tf = nn.TransformerEncoder(
            encoder_layer=encoder_layer,
            num_layers=num_layers,
        )

        if att_pool:
            self.pool = SelfAttentionPooling(d_model=d_model)

        self.film = film

        if d_out is not None:
            self.output = DenseBlock(
                in_features=d_model,
                out_features=d_out,
                use_norm=True,
                activation=act_out,
            )
        else:
            self.output = nn.Identity()

    def forward(self, signal: Tensor, c: Tensor | None = None) -> Tensor:

        signal = self.tf(self.pe(signal))

        if self.att_pool:
            features, weights = self.pool(signal)
        else:
            features = torch.mean(signal, dim=1)
            weights = torch.ones(signal.shape[:-1])

        if self.film is not None:
            features = self.film(features, c)

        features = self.output(features)

        return features, weights
