from typing import Any, List

import numpy as np
import torch
import pandas as pd
import webdataset as wds
from omegaconf import ListConfig
from scipy.signal import fftconvolve
from torch import Tensor
from torch.utils.data import Dataset, DataLoader

from src.util.signals import add_awgn_with_vad


class DataModule:
    def __init__(
        self,
        rir_path: str,
        anechoic_train: str,
        anechoic_valid: str,
        anechoic_test: str,
        data_tuple: ListConfig[str],
        data_split: ListConfig[float],
        snr_range: ListConfig[float],
        num_speech: int,
        num_rir: int,
        num_batch: ListConfig[int],
        hard_sampling: bool,
        speech_representation: Any,
    ) -> None:
        self.rir_path = rir_path
        self.data_split = data_split
        self.snr_range = snr_range
        self.num_speech = num_speech
        self.num_rir = num_rir
        self.num_batch = num_batch
        self.hard_sampling = hard_sampling
        self.speech_representation = speech_representation

        # load rir_dataframe
        rir_dataframe = pd.read_pickle(self.rir_path)

        # scramble dataframe and split according to data_split
        rir_dataframe = rir_dataframe.sample(frac=1).reset_index(drop=True)
        num_rirs = len(rir_dataframe)
        train_end = int(self.data_split[0] * num_rirs)
        val_end = train_end + int(self.data_split[1] * num_rirs)

        rir_subsets = [
            list(rir_dataframe.rir.iloc[:train_end]),
            list(rir_dataframe.rir.iloc[train_end:val_end]),
            list(rir_dataframe.rir.iloc[val_end:]),
        ]

        params = rir_dataframe[["t60", "c50", "t30", "edt", "drr"]]

        param_subsets = [
            params.iloc[:train_end].to_dict(orient="records"),
            params.iloc[train_end:val_end].to_dict(orient="records"),
            params.iloc[val_end:].to_dict(orient="records"),
        ]

        del rir_dataframe

        speech_subsets = [
            anechoic_train,
            anechoic_valid,
            anechoic_test,
        ]

        # create dataloader and datasets for train, valid and test
        self.train_loader, self.valid_loader, self.test_loader = [
            DataLoader(
                dataset=ContrastiveDataset(
                    speech_files=speech_subset,
                    data_tuple=data_tuple,
                    rirs=rir_subset,
                    params=param_subset,
                    num_batch=nb,
                    snr_range=snr_range,
                    num_speech=num_speech,
                    num_rir=num_rir,
                    hard_sampling=hard_sampling,
                    speech_representation=speech_representation,
                ),
                batch_size=1,
            )
            for rir_subset, speech_subset, param_subset, nb in zip(
                rir_subsets,
                speech_subsets,
                param_subsets,
                num_batch,
            )
        ]


class ContrastiveDataset(Dataset):

    def __init__(
        self,
        speech_files: List[str],
        data_tuple: ListConfig[str],
        rirs: List[np.ndarray],
        params: List[dict],
        num_batch: int,
        snr_range: ListConfig[float],
        num_speech: int,
        num_rir: int,
        hard_sampling: bool,
        speech_representation: Any,
    ) -> None:
        super().__init__()
        self.rirs = rirs
        self.params = params
        self.num_batch = num_batch
        self.num_speech = num_speech
        self.num_rir = num_rir
        self.hard_sampling = hard_sampling
        self.speech_representation = speech_representation
        self.snr_range = snr_range

        # endless, shuffled iterator over WebDataset shards for worker-safe streaming
        self.speech_ds = (
            wds.WebDataset(speech_files, shardshuffle=True)
            .shuffle(1000)
            .decode("pil")
            .to_tuple(*data_tuple)
        )
        self._speech_iter = None

    def _next_speech(self) -> np.ndarray:
        if self._speech_iter is None:
            self._speech_iter = iter(self.speech_ds)
        try:
            (dry,) = next(self._speech_iter)
        except StopIteration:
            self._speech_iter = iter(self.speech_ds)
            (dry,) = next(self._speech_iter)
        return np.asarray(dry)

    def __len__(self) -> int:
        return self.num_batch

    def __getitem__(self, index: int) -> tuple[Tensor, torch.LongTensor, List[dict]]:

        rir_inds = np.random.randint(len(self.rirs), size=(self.num_rir,))

        out_sample, snrs = [], []

        for _ in range(self.num_speech):

            if self.hard_sampling:
                speech = self._next_speech()

            for rir_ind in rir_inds:

                snr = np.random.uniform(*self.snr_range)

                if not self.hard_sampling:
                    speech = self._next_speech()

                rev_sample = fftconvolve(speech, self.rirs[rir_ind], mode="full")
                # truncate overlap
                rev_sample = rev_sample[: speech.shape[0]]

                rev_sample = add_awgn_with_vad(rev_sample, snr_db=snr)

                # convert to final speech representation
                signal = Tensor(self.speech_representation(rev_sample))
                signal -= signal.mean()
                signal /= signal.std()

                snrs.append(snr)

                out_sample.append(signal)

        params = [self.params[idx] for idx in rir_inds]

        # add snrs to params
        for param, snr in zip(params, snrs):
            param["snr"] = snr

        return torch.stack(out_sample), torch.LongTensor(rir_inds), params
