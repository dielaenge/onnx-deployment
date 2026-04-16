import math
from typing import Tuple, List, Union
from einops import reduce
import pickle
import torch
import torch.nn as nn
from torch import Tensor


class DenseBlock(nn.Module):
    """MLP building block"""

    def __init__(
        self,
        in_features: int,
        out_features: int,
        use_norm: bool = True,
        activation: Union[str, None] = "relu",
    ) -> None:
        super().__init__()

        self.use_norm = use_norm

        if activation == "relu":
            self.activation = nn.ReLU()
        elif activation == "prelu":
            self.activation = nn.PReLU()
        elif activation == "tanh":
            self.activation = nn.Tanh()
        elif activation == "sigmoid":
            self.activation = nn.Sigmoid()
        elif activation == "softmax":
            self.activation = nn.Softmax()
        elif activation == "swish":
            self.activation = nn.SiLU()
        elif activation is None:
            self.activation = nn.Identity()
        else:
            raise ValueError("Unknown activation function.")

        self.linear = nn.Linear(in_features=in_features, out_features=out_features)

        if self.use_norm:
            self.norm = nn.LayerNorm(normalized_shape=out_features)
        else:
            self.norm = nn.Identity()

    def forward(self, tensor: Tensor) -> Tensor:
        return self.activation(self.norm(self.linear(tensor)))


class RegressionHead(nn.Module):
    """Multi-layer perceptron for downstream tasks"""

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        output_dim: int,
        hidden_act: str = "relu",
        output_act: Union[str, None] = "relu",
        num_blocks: int = 1,
        p_drop: float = 0.0,
        use_norm: bool = True,
        state: str | None = None,
    ) -> None:
        super().__init__()

        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim

        self.input_layer = nn.Linear(in_features=input_dim, out_features=hidden_dim)

        self.hidden_layers = nn.ModuleList()
        [
            self.hidden_layers.append(
                DenseBlock(
                    in_features=hidden_dim,
                    out_features=hidden_dim,
                    use_norm=use_norm,
                    activation=hidden_act,
                )
            )
            for _ in range(num_blocks)
        ]

        self.drop = nn.Dropout(p=p_drop)

        self.output = DenseBlock(
            in_features=hidden_dim,
            out_features=output_dim,
            use_norm=False,
            activation=output_act,
        )

        # load model state
        if state is not None:
            with open(state, "rb") as handle:
                state_dict = pickle.load(handle)
            self.load_state_dict(state_dict["adapter_state"])
            print(f"MLP @ {hex(id(self))} state succesfully loaded:\n{state}")

    def forward(self, x: Tensor) -> Tensor:
        x = self.input_layer(x)
        for layer in self.hidden_layers:
            x = layer(x)
        x = self.drop(x)
        return self.output(x)
