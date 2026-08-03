from typing import List

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.distributed as dist
from torch import Tensor


def kld_gaussian_diag(mu1: Tensor, mu2: Tensor, var2: Tensor) -> Tensor:
    r"""
    Kullback-Leibler Divergence between two multivariate Gaussians
    Special case: p1 has identity covariance matrix

    Args:
        mu1 (torch.Tensor): mean of the first Gaussian
        mu2 (torch.Tensor): mean of the second Gaussian
        sigma2 (torch.Tensor): standard deviation of the second Gaussian

    Returns:
        torch.Tensor: Kullback-Leibler Divergence
    """
    dmu = (mu2 - mu1) ** 2
    # mean across all latent variables
    kld = torch.mean(1 / var2 + dmu / var2 - 1 + torch.log(var2), dim=-1)
    return kld.mean()


def quantile_loss(
    preds: Tensor,
    target: Tensor,
    quantiles: List[float] = [0.05, 0.5, 0.95],
) -> Tensor:
    """
    Computes the quantile loss (pinball loss) for given predictions and targets.

    Args:
        preds (Tensor): Predicted quantiles, shape (..., num_quantiles)
        target (Tensor): Ground truth values, shape compatible with preds
        quantiles (List[float]): List of quantiles, length must match preds' last dimension

    Returns:
        Tensor: Scalar quantile loss
    """
    assert preds.shape[-1] == len(
        quantiles
    ), "Number of quantiles must match predictions"
    losses = []
    for i, q in enumerate(quantiles):
        pred = preds[..., i]
        errors = target - pred
        loss = torch.max((q - 1) * errors, q * errors)
        losses.append(loss)
    total_loss = torch.stack(losses, dim=-1).sum(dim=-1).mean()
    return total_loss


def compute_cross_entropy(p, q):
    q = F.log_softmax(q, dim=-1)
    loss = torch.sum(p * q, dim=-1)
    return -loss.mean()


def stablize_logits(logits):
    logits_max, _ = torch.max(logits, dim=-1, keepdim=True)
    logits = logits - logits_max.detach()
    return logits


def is_dist_avail_and_initialized():
    if not dist.is_available():
        return False
    if not dist.is_initialized():
        return False
    return True


def get_rank():
    if not is_dist_avail_and_initialized():
        return 0
    return dist.get_rank()


class MultiPosConLoss(nn.Module):
    """
    Multi-Positive Contrastive Loss: https://arxiv.org/pdf/2306.00984.pdf

    This implementation is not used for multi GPU training.
    """

    def __init__(self, temperature=0.1):
        super(MultiPosConLoss, self).__init__()
        self.temperature = temperature
        self.logits_mask = None
        self.mask = None
        self.last_local_batch_size = None

    def set_temperature(self, temp=0.1):
        self.temperature = temp

    def forward(self, feats, labels):

        feats = F.normalize(feats, dim=-1, p=2)
        local_batch_size = feats.size(0)

        # compute the mask based on labels
        if local_batch_size != self.last_local_batch_size:
            mask = (
                torch.eq(labels.view(-1, 1), labels.contiguous().view(1, -1))
                .float()
                .to(feats)
            )
            self.logits_mask = torch.scatter(
                torch.ones_like(mask),
                1,
                torch.arange(mask.shape[0]).view(-1, 1).to(feats.device)
                + local_batch_size * get_rank(),
                0,
            )

            self.last_local_batch_size = local_batch_size
            self.mask = mask * self.logits_mask

        mask = self.mask

        # compute logits
        logits = torch.matmul(feats, feats.T) / self.temperature
        logits = logits - (1 - self.logits_mask) * 1e9

        # optional: minus the largest logit to stablize logits
        logits = stablize_logits(logits)

        # compute ground-truth distribution
        p = mask / mask.sum(1, keepdim=True).clamp(min=1.0)
        loss = compute_cross_entropy(p, logits)

        return loss
