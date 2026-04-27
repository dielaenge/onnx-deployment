import pickle
from typing import Tuple, Sequence
import torch.nn as nn
from torch import Tensor

from einops import rearrange

"""Conv modules"""


def Conv1d(*args, **kwargs) -> nn.Module:
    return nn.Conv1d(*args, **kwargs)


def ConvTranspose1d(*args, **kwargs) -> nn.Module:
    return nn.ConvTranspose1d(*args, **kwargs)


def Downsample1d(
    in_channels: int,
    out_channels: int,
    factor: int,
    kernel_multiplier: int = 2,
) -> nn.Module:
    assert kernel_multiplier % 2 == 0, "Kernel multiplier must be even"

    return Conv1d(
        in_channels=in_channels,
        out_channels=out_channels,
        kernel_size=factor * kernel_multiplier + 1,
        stride=factor,
        padding=factor * (kernel_multiplier // 2),
    )


def Upsample1d(
    in_channels: int,
    out_channels: int,
    factor: int,
    pads: int,
    kernel_multiplier: int = 2,
) -> nn.Module:
    # if factor == [1, 1]:
    #     return ConvTranspose2d(
    #         in_channels=in_channels,
    #         out_channels=out_channels,
    #         kernel_size=(3, 3),
    #         # padding=pads,
    #         # output_padding=pads,
    #     )

    padding = factor * (kernel_multiplier // 2)
    # output_padding = [fact % 2 for fact in factor]
    # output_padding = [0, 0]
    foo = 1

    return ConvTranspose1d(
        in_channels=in_channels,
        out_channels=out_channels,
        kernel_size=factor,
        stride=factor,
        # padding=padding,
    )


class ConvBlock1d(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int = 3,
        stride: int = 1,
        padding: int = 1,
        dilation: int = 1,
        num_groups: int = 8,
        use_norm: bool = True,
    ) -> None:
        super().__init__()

        self.groupnorm = (
            nn.GroupNorm(num_groups=num_groups, num_channels=in_channels)
            if use_norm
            else nn.Identity()
        )

        # hard coded padding for now
        padding = (kernel_size - 1) // 2

        self.activation = nn.SiLU()
        self.project = Conv1d(
            in_channels=in_channels,
            out_channels=out_channels,
            kernel_size=kernel_size,
            stride=stride,
            padding=padding,
            dilation=dilation,
        )

    def forward(self, x: Tensor) -> Tensor:
        x = self.groupnorm(x)
        x = self.activation(x)
        return self.project(x)


class ResnetBlock1d(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int = 3,
        stride: int = 1,
        padding: int = 1,
        dilation: int = 1,
        use_norm: bool = True,
        num_groups: int = 8,
    ) -> None:
        super().__init__()

        self.block1 = ConvBlock1d(
            in_channels=in_channels,
            out_channels=out_channels,
            kernel_size=kernel_size,
            stride=stride,
            padding=padding,
            dilation=dilation,
            use_norm=use_norm,
            num_groups=num_groups,
        )

        self.block2 = ConvBlock1d(
            in_channels=out_channels,
            out_channels=out_channels,
            use_norm=use_norm,
            num_groups=num_groups,
        )

        self.to_out = (
            Conv1d(
                in_channels=in_channels,
                out_channels=out_channels,
                kernel_size=1,
            )
            if in_channels != out_channels
            else nn.Identity()
        )

    def forward(self, x: Tensor) -> Tensor:
        h = self.block1(x)
        h = self.block2(h)
        return h + self.to_out(x)


class DownsampleBlock1d(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        *,
        factor: int,
        num_groups: int,
        num_layers: int,
        kernel_size: int,
        stride: int,
    ):
        super().__init__()

        if factor == 1:
            self.downsample = nn.Identity()
        else:
            self.downsample = Downsample1d(
                in_channels=in_channels, out_channels=out_channels, factor=factor
            )

        self.blocks = nn.ModuleList(
            [
                ResnetBlock1d(
                    in_channels=out_channels,
                    out_channels=out_channels,
                    num_groups=num_groups,
                    kernel_size=kernel_size,
                    stride=stride,
                )
                for _ in range(num_layers)
            ]
        )

    def forward(self, x: Tensor) -> Tensor:
        x = self.downsample(x)
        for block in self.blocks:
            x = block(x)
        return x


class UpsampleBlock1d(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        *,
        factor: int,
        num_groups: int,
        num_layers: int,
        kernel_size: int,
        stride: int,
        pads: int,
    ):
        super().__init__()

        self.upsample = Upsample1d(
            in_channels=in_channels,
            out_channels=out_channels,
            factor=factor,
            pads=pads,
        )

        self.blocks = nn.ModuleList(
            [
                ResnetBlock1d(
                    in_channels=out_channels,
                    out_channels=out_channels,
                    num_groups=num_groups,
                    kernel_size=kernel_size,
                    stride=stride,
                )
                for _ in range(num_layers)
            ]
        )

    def forward(self, x: Tensor) -> Tensor:
        x = self.upsample(x)
        for block in self.blocks:
            x = block(x)
        return x


"""Encoder"""


class CNNEncoder(nn.Module):
    def __init__(
        self,
        in_channels: int,
        channels: int,
        multipliers: Sequence[int],
        factors: Sequence[int],
        num_blocks: Sequence[int],
        kernel_sizes: Sequence[int],
        strides: Sequence[int],
        pads: Sequence[int],
        latent_proj: int | None = None,
        resnet_groups: int = 8,
        state: str | None = None,
    ):
        super().__init__()

        self.num_layers = len(kernel_sizes)
        # self.downsample_factor = patch_size * prod(factors)
        self.out_channels = channels * multipliers[-1]

        assert len(factors) == self.num_layers and len(num_blocks) == self.num_layers

        self.to_in = ConvBlock1d(
            in_channels=in_channels,
            out_channels=channels,
            kernel_size=kernel_sizes[0],
            stride=strides[0],
            use_norm=False,
        )

        self.encoder_blocks = nn.ModuleList(
            [
                DownsampleBlock1d(
                    in_channels=channels * multipliers[i],
                    out_channels=channels * multipliers[i + 1],
                    factor=factor,
                    num_groups=resnet_groups,
                    num_layers=blocks,
                    kernel_size=kernel,
                    stride=stride,
                )
                for i, (kernel, stride, blocks, factor) in enumerate(
                    zip(kernel_sizes[1:], strides[1:], num_blocks[1:], factors[1:])
                )
            ]
        )

        if latent_proj is not None:
            self.to_out = nn.Linear(
                in_features=self.out_channels,
                out_features=latent_proj,
            )
        else:
            self.to_out = nn.Identity()

        if state is not None:
            with open(state, "rb") as handle:
                state = pickle.load(handle)
            self.load_state_dict(state["encoder_state"])

    def forward(self, x: Tensor) -> Tensor:
        x = self.to_in(x)

        for block in self.encoder_blocks:
            x = block(x)

        if isinstance(self.to_out, nn.Linear):
            x = self.to_out(rearrange(x, "b c h w -> b h w c"))
            x = rearrange(x, "b h w c -> b c h w")
        else:
            x = self.to_out(x)

        return x


"""Decoder"""


class CNNDecoder(nn.Module):
    def __init__(
        self,
        out_channels: int,
        channels: int,
        multipliers: Sequence[int],
        factors: Sequence[int],
        num_blocks: Sequence[int],
        kernel_sizes: Sequence[int],
        strides: Sequence[int],
        pads: Sequence[int],
        latent_proj: int | None = None,
        resnet_groups: int = 8,
        state: str | None = None,
    ):
        super().__init__()
        self.num_layers = len(kernel_sizes)
        # self.downsample_factor = patch_size * prod(factors)
        self.out_channels = channels * multipliers[-1]

        assert len(factors) == self.num_layers and len(num_blocks) == self.num_layers

        self.decoder_blocks = nn.ModuleList(
            [
                UpsampleBlock1d(
                    in_channels=channels * multipliers[i],
                    out_channels=channels * multipliers[i + 1],
                    factor=factor,
                    num_groups=resnet_groups,
                    num_layers=blocks,
                    kernel_size=kernel,
                    stride=stride,
                    pads=pad,
                )
                for i, (kernel, stride, blocks, factor, pad) in enumerate(
                    zip(
                        kernel_sizes[:-1],
                        strides[:-1],
                        num_blocks[:-1],
                        factors[:-1],
                        pads[:-1],
                    )
                )
            ]
        )

        if latent_proj is not None:
            self.to_in = nn.Linear(
                in_features=latent_proj,
                out_features=channels * multipliers[0],
            )
        else:
            self.to_in = nn.Identity()

        self.to_out = nn.Conv1d(
            in_channels=channels * multipliers[-1],
            out_channels=out_channels,
            kernel_size=kernel_sizes[-1],
            stride=strides[-1],
            padding=[(k - 1) // 2 for k in kernel_sizes[-1]],
        )

        if state is not None:
            with open(state, "rb") as handle:
                state = pickle.load(handle)
            self.load_state_dict(state["decoder_state"])

    def forward(self, x: Tensor) -> Tensor:

        if isinstance(self.to_in, nn.Linear):
            x = self.to_in(rearrange(x, "b c h w -> b h w c"))
            x = rearrange(x, "b h w c -> b c h w")
        else:
            x = self.to_in(x)

        for block in self.decoder_blocks:
            x = block(x)
        x = self.to_out(x)
        return x
