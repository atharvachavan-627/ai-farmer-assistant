"""
Model creation module for AI Farmer Assistant.

Provides MobileNetV2 architecture with ImageNet pretrained weights,
adapted for plant disease classification.
"""

from typing import Tuple
import torch
import torch.nn as nn
from torchvision.models import mobilenet_v2, MobileNet_V2_Weights


def create_mobilenetv2(
    num_classes: int = 13,
    pretrained: bool = True,
    freeze_features: bool = True,
    dropout_p: float = 0.2
) -> nn.Module:
    """
    Builds a MobileNetV2 model configured for plant disease classification.
    
    Args:
        num_classes: Number of disease target classes (default: 13)
        pretrained: Whether to load ImageNet pretrained weights (default: True)
        freeze_features: Whether to freeze feature extractor layers (default: True)
        dropout_p: Dropout probability before the classification head (default: 0.2)
        
    Returns:
        Configured nn.Module ready for forward pass / training.
    """
    weights = MobileNet_V2_Weights.DEFAULT if pretrained else None
    model = mobilenet_v2(weights=weights)

    # Freeze feature extractor layers if requested
    if freeze_features:
        for param in model.features.parameters():
            param.requires_grad = False

    # Extract classifier input dimension (1280 for MobileNetV2)
    in_features = model.classifier[1].in_features

    # Replace the final classification head
    model.classifier = nn.Sequential(
        nn.Dropout(p=dropout_p, inplace=False),
        nn.Linear(in_features=in_features, out_features=num_classes, bias=True)
    )

    # Ensure classifier parameters are trainable
    for param in model.classifier.parameters():
        param.requires_grad = True

    return model


def get_parameter_counts(model: nn.Module) -> Tuple[int, int]:
    """
    Returns (total_parameters, trainable_parameters) for a given PyTorch model.
    """
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return total_params, trainable_params
