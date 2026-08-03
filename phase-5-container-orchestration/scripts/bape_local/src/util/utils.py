import random
import pickle
from pathlib import Path
from datetime import datetime
from typing import Optional, Literal, Tuple, List

import numpy as np
import torch
from soundfile import write


def seed_everything(seed: Optional[int] = None) -> None:
    """
    Sets the random seed for reproducibility across various libraries.
    """
    if seed is None:
        seed = random.randint(0, 2**32 - 1)
    print(f"Using seed: {seed}")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    # torch.backends.cudnn.deterministic = True
    # torch.use_deterministic_algorithms(True, warn_only=True)


def get_device(id: Optional[Literal["cpu", "cuda"]]) -> torch.device:
    """
    Determines the appropriate device (CPU or GPU) for PyTorch operations.

    Returns:
        torch.device: A PyTorch device object representing either "cuda" if a GPU is available, or "cpu" if no GPU is available.
    """
    # Check if the user has specified a device
    if id == "cuda" and torch.cuda.is_available():
        device = torch.device("cuda")
    if id == "cuda" and not torch.cuda.is_available():
        device = torch.device("cpu")
        print("No GPU available, using CPU.")
    if id == "cpu":
        device = torch.device("cpu")
    return device


def create_log_dir(subdir: Optional[str], debug: bool) -> Tuple[Path, Path]:
    """
    Creates a directory structure for logging and returns the paths.

    This function generates a timestamped directory inside a "logs/" folder
    and creates a subdirectory named "outputs" within it. If the directories
    already exist, they are not recreated.

    Returns:
        Tuple[str, str]: A tuple containing the path to the "outputs" directory
        and the path to the main log directory.
    """
    datestr = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    pth = Path("logs/debug") if debug else Path("logs/")
    if subdir is not None:
        pth = pth / subdir
    log_dir = pth / datestr
    out_dir = log_dir / "outputs"
    log_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    return log_dir, out_dir


def write_outputs(
    outputs: List[dict],
    out_dir: Path,
    num_batch: Optional[int] = None,
) -> None:
    """Writes the outputs from speech2fdn to the specified directory."""

    if num_batch is None:
        num_batch = len(outputs)
    else:
        assert num_batch <= len(
            outputs
        ), f"num_batch must be < len(outputs): ({len(outputs)})"

    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)

    write_wav = lambda data, idx, i, suffix: write(
        file=out_dir / f"{idx:03d}_{i:03d}{suffix}.wav",
        data=data,
        samplerate=48000,
    )

    for idx, output in enumerate(outputs[:num_batch]):
        for i, (wet, wet_fdn, dry, rir, rir_fdn, ext_param) in enumerate(
            zip(
                output["wet"],
                output["wet_fdn"],
                output["dry"],
                output["rir"],
                output["rir_fdn"],
                output["ext_params"],
            )
        ):
            # normalize
            wet /= np.max(np.abs(wet))
            wet_fdn /= np.max(abs(wet_fdn))
            dry /= np.max(np.abs(dry))
            rir /= np.max(np.abs(rir))
            rir_fdn /= np.max(np.abs(rir_fdn))
            # write
            write_wav(wet, idx, i, "_wet")
            write_wav(wet_fdn, idx, i, "_wet_fdn")
            write_wav(dry, idx, i, "_dry")
            write_wav(rir, idx, i, "_rir")
            write_wav(rir_fdn, idx, i, "_rir_fdn")

            ext_param_path = out_dir / f"{idx:03d}_{i:03d}_ext_param.pkl"
            with ext_param_path.open("wb") as f:
                pickle.dump(ext_param, f)
