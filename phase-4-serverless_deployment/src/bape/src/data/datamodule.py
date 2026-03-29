from typing import List
from torch.utils.data import DataLoader
from webdataset import WebDataset


class DataModule:
    def __init__(
        self,
        train_url: str,
        valid_url: str,
        test_url: str,
        data_tuple: List[str],
        batch_size: int,
        num_workers: int,
    ) -> None:

        self.batch_size = batch_size
        self.num_workers = num_workers
        self.data_tuple = data_tuple

        train_dataset, valid_dataset, test_dataset = [
            WebDataset(url, shardshuffle=shuff)
            .shuffle(128 if shuff else 0)
            .decode("pil")
            .to_tuple(*data_tuple)
            for shuff, url in zip(
                [True, False, False], [train_url, valid_url, test_url]
            )
        ]

        self.train_loader = DataLoader(
            dataset=train_dataset,
            batch_size=batch_size,
            num_workers=num_workers,
            drop_last=False,
        )

        self.valid_loader = DataLoader(
            dataset=valid_dataset,
            batch_size=batch_size,
            num_workers=num_workers,
            drop_last=False,
        )

        self.test_loader = DataLoader(
            dataset=test_dataset,
            batch_size=batch_size,
            num_workers=num_workers,
            drop_last=False,
        )

    def train_dataloader(self) -> DataLoader:
        return self.train_loader

    def val_dataloader(self) -> DataLoader:
        return self.valid_loader

    def test_dataloader(self) -> DataLoader:
        return self.test_loader
