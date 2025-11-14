import os
from typing import List, Optional
from pathlib import Path


def make_dirs(out_path: str, subsets: list) -> None:
    """Create sub-directories"""
    if os.path.exists(out_path):
        raise OSError("Output directory already exists.")
    for subfolder in subsets:
        os.makedirs(f"{out_path}/{subfolder}")


def get_file_list(
    path: str,
    pattern: Optional[str] = None,
    suffix: List[str] = [".wav", ".flac"],
) -> list:
    """Retrieve all files of a  specific type"""
    file_list = []
    pth = Path(path)
    for fname in pth.glob("**/*"):
        # ensure audio format and filter out hidden dot files
        if fname.suffix in suffix and fname.name[0] != ".":
            if pattern is not None:
                if pattern in fname.parts:
                    file_list.append(str(fname.resolve()))
            else:
                file_list.append(str(fname.resolve()))
    return file_list


def split_list(long_list: list, ratios: List[float]) -> list:
    "Split a list into subsets according to ratios"
    assert len(ratios) >= 2, "len(ratios) should be >= 2."
    # get sizes of specified subsets
    subset_sizes = [int(ratio * len(long_list)) for ratio in ratios]
    # separate all but the last subset
    subsets = [
        [long_list.pop() for _ in range(subset_size)]
        for subset_size in subset_sizes[:-1]
    ]
    # append the left-overs
    subsets.append(long_list)
    return subsets