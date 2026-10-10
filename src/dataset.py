"""
PyTorch Dataset and DataLoader pipeline for AI Farmer Assistant.

Uses torchvision.datasets.ImageFolder with validated train, validation, and test splits.
"""

from pathlib import Path
from typing import Tuple, Dict, Optional
import torch
from torchvision import datasets
from torch.utils.data import DataLoader

from src.preprocessing import train_transform, val_test_transform

# Default configurations
DEFAULT_BATCH_SIZE = 32
DEFAULT_NUM_WORKERS = 0

# Base project path resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SPLIT_DIR = PROJECT_ROOT / "data" / "processed" / "tomato_potato_split"


def get_datasets(
    split_dir: Optional[Path] = None,
    train_tf=train_transform,
    val_tf=val_test_transform,
    test_tf=val_test_transform
) -> Tuple[datasets.ImageFolder, datasets.ImageFolder, datasets.ImageFolder]:
    """
    Creates and returns the train, validation, and test ImageFolder datasets.
    """
    base_dir = Path(split_dir) if split_dir else DEFAULT_SPLIT_DIR
    train_dir = base_dir / "train"
    val_dir = base_dir / "val"
    test_dir = base_dir / "test"

    if not train_dir.exists():
        raise FileNotFoundError(f"Training directory not found at: {train_dir}")
    if not val_dir.exists():
        raise FileNotFoundError(f"Validation directory not found at: {val_dir}")
    if not test_dir.exists():
        raise FileNotFoundError(f"Test directory not found at: {test_dir}")

    train_dataset = datasets.ImageFolder(root=str(train_dir), transform=train_tf)
    val_dataset = datasets.ImageFolder(root=str(val_dir), transform=val_tf)
    test_dataset = datasets.ImageFolder(root=str(test_dir), transform=test_tf)

    return train_dataset, val_dataset, test_dataset


def get_dataloaders(
    train_dataset: datasets.ImageFolder,
    val_dataset: datasets.ImageFolder,
    test_dataset: datasets.ImageFolder,
    batch_size: int = DEFAULT_BATCH_SIZE,
    num_workers: int = DEFAULT_NUM_WORKERS,
    pin_memory: bool = False
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    """
    Creates and returns PyTorch DataLoaders for train, validation, and test datasets.
    - Training: shuffle=True
    - Validation: shuffle=False
    - Testing: shuffle=False
    """
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=pin_memory
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin_memory
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin_memory
    )

    return train_loader, val_loader, test_loader
