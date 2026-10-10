"""
Image preprocessing pipelines for AI Farmer Assistant disease classification model.

Input: 224x224 RGB image
Outputs: Normalized PyTorch tensor of shape [3, 224, 224], dtype float32
"""

import torch
from torchvision import transforms

# -------------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------------
IMAGE_SIZE = 224

# ImageNet normalization statistics
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def get_train_transform(image_size: int = IMAGE_SIZE):
    """
    Conservative training augmentation pipeline appropriate for plant disease classification.
    
    Augmentations:
    1. RandomResizedCrop: 224x224, scale=(0.85, 1.0), ratio=(0.9, 1.1)
       (Conservative crop that retains 85-100% area to preserve disease symptoms)
    2. RandomHorizontalFlip: p=0.5
       (Natural biological symmetry, does not introduce artifacts)
    3. Mild ColorJitter: brightness=0.15, contrast=0.15, saturation=0.10, hue=0.02
       (Simulates mild sunlight/camera variation while preserving natural leaf & lesion colors)
    4. ToTensor: Converts PIL image [0, 255] to torch.float32 [0.0, 1.0]
    5. ImageNet normalization: Zero-centers channels using ImageNet mean & std
    """
    return transforms.Compose([
        transforms.RandomResizedCrop(
            size=(image_size, image_size),
            scale=(0.85, 1.0),
            ratio=(0.9, 1.1)
        ),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.ColorJitter(
            brightness=0.15,
            contrast=0.15,
            saturation=0.10,
            hue=0.02
        ),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=IMAGENET_MEAN,
            std=IMAGENET_STD
        )
    ])


def get_val_test_transform(image_size: int = IMAGE_SIZE):
    """
    Validation and test evaluation pipeline (deterministic, no augmentation).
    
    Transformations:
    1. Resize: Exactly 224x224
    2. ToTensor: Converts PIL image [0, 255] to torch.float32 [0.0, 1.0]
    3. ImageNet normalization: Zero-centers channels using ImageNet mean & std
    """
    return transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=IMAGENET_MEAN,
            std=IMAGENET_STD
        )
    ])


# Standard default instances
train_transform = get_train_transform()
val_test_transform = get_val_test_transform()


def unnormalize(tensor: torch.Tensor, mean=IMAGENET_MEAN, std=IMAGENET_STD) -> torch.Tensor:
    """
    Invert ImageNet normalization on a tensor of shape [3, H, W] to restore [0, 1] range.
    Clamps result to [0.0, 1.0].
    """
    tensor_copy = tensor.clone().detach()
    for channel, (m, s) in enumerate(zip(mean, std)):
        tensor_copy[channel] = tensor_copy[channel] * s + m
    return torch.clamp(tensor_copy, 0.0, 1.0)
