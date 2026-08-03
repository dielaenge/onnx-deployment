import os
import random
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
import numpy as np
import pandas as pd
from tqdm import trange
from webdataset import ShardWriter
from soundfile import read
from librosa import resample
from omegaconf import ListConfig

# import matplotlib.pyplot as plt

from src.util.signals import (
    AudioStream,
    reverberate,
    remove_pre_delay,
    fix_length,
    add_awgn_with_vad,
)
from src.util.files import get_file_list, split_list
from src.util.utils import seed_everything


def generate(
    fs: int,
    duration: float,
    data_split: ListConfig[float],
    speech_path: str,
    out_path: str,
    write_flag: bool = True,
    seed: int = 42,
) -> None:
    """rir_dataset generation for distance fingerprinting"""

    seed_everything(seed)

    # subset names
    prefixes = ["train", "valid", "test"]

    speech_subsets = split_list(get_file_list(speech_path), data_split)

    for speech_subset, prefix in zip(speech_subsets, prefixes):
        # retrieves anechoic source and noise segments
        speech_stream = AudioStream(
            file_list=speech_subset,
            sr=fs,
            duration=duration,
            seed=seed,
        )

        wrapped = False
        sample_count = 0

        # init shardwriter
        if write_flag:
            sink = ShardWriter(f"{out_path}/{prefix}-%04d.tar", maxsize=1e9)
            sink.verbose = False

        while not wrapped:
            dry, wrapped = speech_stream.next_segment()

            out_dict = {
                "__key__": f"sample{sample_count:08d}",
                "dry.pyd": dry.astype(np.float32),
            }

            sample_count += 1

            if write_flag:
                sink.write(out_dict)

        print("Wrapped!")
        print(f"{prefix}: {sample_count} samples")

        # close subset sink
        if write_flag:
            sink.close()
