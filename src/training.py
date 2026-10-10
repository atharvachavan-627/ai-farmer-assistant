"""
Training configuration, loss functions, optimizers, and utilities for AI Farmer Assistant.
"""

from typing import Tuple, Dict, Any, Optional
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from sklearn.utils.class_weight import compute_class_weight

# Hyperparameters
DEFAULT_LEARNING_RATE = 1e-3
DEFAULT_WEIGHT_DECAY = 1e-4
DEFAULT_SCHEDULER_FACTOR = 0.5
DEFAULT_SCHEDULER_PATIENCE = 2
DEFAULT_EARLY_STOPPING_PATIENCE = 5


def compute_dataset_class_weights(
    train_dataset,
    num_classes: int = 13,
    device: Optional[torch.device] = None
) -> torch.Tensor:
    """
    Computes balanced class weights from the training dataset label distribution:
    weight = N_samples / (N_classes * N_class_samples)
    
    Returns:
        torch.Tensor of shape [num_classes] on the specified device.
    """
    train_labels = np.array([label for _, label in train_dataset.samples])
    
    weights = compute_class_weight(
        class_weight="balanced",
        classes=np.arange(num_classes),
        y=train_labels
    )
    
    class_weights_tensor = torch.tensor(weights, dtype=torch.float32)
    if device is not None:
        class_weights_tensor = class_weights_tensor.to(device)
        
    return class_weights_tensor


class EarlyStopping:
    """
    Early stopping monitor to halt training when validation metric stops improving.
    """
    def __init__(
        self,
        patience: int = DEFAULT_EARLY_STOPPING_PATIENCE,
        min_delta: float = 1e-4,
        mode: str = "min"
    ):
        self.patience = patience
        self.min_delta = min_delta
        self.mode = mode
        self.counter = 0
        self.best_score = None
        self.early_stop = False

    def __call__(self, val_metric: float) -> bool:
        if self.best_score is None:
            self.best_score = val_metric
            return False

        if self.mode == "min":
            improved = val_metric < (self.best_score - self.min_delta)
        else:
            improved = val_metric > (self.best_score + self.min_delta)

        if improved:
            self.best_score = val_metric
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True

        return self.early_stop


def get_training_components(
    model: nn.Module,
    train_dataset,
    num_classes: int = 13,
    lr: float = DEFAULT_LEARNING_RATE,
    weight_decay: float = DEFAULT_WEIGHT_DECAY,
    device: Optional[torch.device] = None
) -> Tuple[nn.Module, torch.optim.Optimizer, torch.optim.lr_scheduler.ReduceLROnPlateau, EarlyStopping]:
    """
    Sets up the loss function, optimizer, scheduler, and early stopping monitor.
    
    - Loss: Class-weighted CrossEntropyLoss
    - Optimizer: Adam on trainable parameters (classifier)
    - Scheduler: ReduceLROnPlateau (factor=0.5, patience=2, mode='min')
    - Early Stopping: EarlyStopping (patience=5, mode='min')
    """
    # 1. Class weights & Loss
    class_weights = compute_dataset_class_weights(train_dataset, num_classes=num_classes, device=device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    # 2. Optimizer for trainable parameters
    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.Adam(
        trainable_params,
        lr=lr,
        weight_decay=weight_decay
    )

    # 3. Learning Rate Scheduler
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=DEFAULT_SCHEDULER_FACTOR,
        patience=DEFAULT_SCHEDULER_PATIENCE
    )

    # 4. Early Stopping
    early_stopping = EarlyStopping(
        patience=DEFAULT_EARLY_STOPPING_PATIENCE,
        mode="min"
    )

    return criterion, optimizer, scheduler, early_stopping
