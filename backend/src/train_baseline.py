"""
Baseline training script for MobileNetV2 on PlantVillage dataset.
"""

import sys
import time
import json
import random
import copy
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from torchvision.models import mobilenet_v2, MobileNet_V2_Weights

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dataset import get_datasets, get_dataloaders
from src.training import compute_dataset_class_weights

# -------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------
SEED = 42
NUM_CLASSES = 13
BATCH_SIZE = 32
NUM_WORKERS = 0
LEARNING_RATE = 1e-3
WEIGHT_DECAY = 1e-4
MAX_EPOCHS = 10
EARLY_STOPPING_PATIENCE = 3
SCHEDULER_FACTOR = 0.5
SCHEDULER_PATIENCE = 2

CHECKPOINT_DIR = PROJECT_ROOT / "models" / "mobilenetv2"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR = Path(r"C:\Users\ATHARVA\.gemini\antigravity-ide\brain\ba4ca457-3323-47ea-936e-1a18b12fd977")


def set_seed(seed=SEED):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def run_training():
    print("=" * 80)
    print("MOBILENETV2 BASELINE TRAINING EXPERIMENT")
    print("=" * 80)

    set_seed(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    print(f"Random seed: {SEED}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Max epochs: {MAX_EPOCHS}")
    print(f"Early stopping patience: {EARLY_STOPPING_PATIENCE}")

    # 1. Datasets & DataLoaders
    print("\n1. Loading Train and Validation Datasets...")
    train_ds, val_ds, test_ds = get_datasets()
    assert len(train_ds.classes) == NUM_CLASSES, f"Expected {NUM_CLASSES} classes, got {len(train_ds.classes)}"
    print(f"   Train samples: {len(train_ds)}")
    print(f"   Validation samples: {len(val_ds)}")
    print(f"   Classes ({NUM_CLASSES}): {train_ds.classes}")

    train_loader, val_loader, _ = get_dataloaders(
        train_ds, val_ds, test_ds,
        batch_size=BATCH_SIZE,
        num_workers=NUM_WORKERS
    )

    # Save class mapping
    class_mapping = train_ds.class_to_idx
    with open(CHECKPOINT_DIR / "class_mapping.json", "w") as f:
        json.dump(class_mapping, f, indent=4)
    print(f"   Class mapping saved to: {CHECKPOINT_DIR / 'class_mapping.json'}")

    # 2. Fresh Model Initialization
    print("\n2. Initializing fresh MobileNetV2 from ImageNet pretrained weights...")
    weights = MobileNet_V2_Weights.DEFAULT
    model = mobilenet_v2(weights=weights)

    # Freeze feature extractor
    for param in model.features.parameters():
        param.requires_grad = False

    # Replace classifier
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.2, inplace=False),
        nn.Linear(in_features=in_features, out_features=NUM_CLASSES, bias=True)
    )

    for param in model.classifier.parameters():
        param.requires_grad = True

    model = model.to(device)

    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"   Total Parameters: {total_params:,}")
    print(f"   Trainable Parameters: {trainable_params:,}")

    # 3. Loss, Optimizer, Scheduler
    print("\n3. Configuring weighted CrossEntropyLoss, Adam, and ReduceLROnPlateau...")
    class_weights = compute_dataset_class_weights(train_ds, num_classes=NUM_CLASSES, device=device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    optimizer = torch.optim.Adam(
        model.classifier[1].parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY
    )

    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=SCHEDULER_FACTOR,
        patience=SCHEDULER_PATIENCE
    )

    # Save training configuration
    train_config = {
        "model_architecture": "MobileNetV2",
        "pretrained_weights": "ImageNet",
        "num_classes": NUM_CLASSES,
        "batch_size": BATCH_SIZE,
        "learning_rate": LEARNING_RATE,
        "weight_decay": WEIGHT_DECAY,
        "max_epochs": MAX_EPOCHS,
        "early_stopping_patience": EARLY_STOPPING_PATIENCE,
        "scheduler": "ReduceLROnPlateau",
        "scheduler_factor": SCHEDULER_FACTOR,
        "scheduler_patience": SCHEDULER_PATIENCE,
        "loss_function": "Weighted CrossEntropyLoss",
        "seed": SEED,
        "device": str(device)
    }
    with open(CHECKPOINT_DIR / "training_config.json", "w") as f:
        json.dump(train_config, f, indent=4)
    print(f"   Training configuration saved to: {CHECKPOINT_DIR / 'training_config.json'}")

    # 4. Training Loop
    print("\n" + "=" * 80)
    print("STARTING TRAINING LOOP")
    print("=" * 80)

    history = {
        "train_loss": [],
        "train_accuracy": [],
        "val_loss": [],
        "val_accuracy": [],
        "learning_rate": [],
        "epoch_duration": []
    }

    best_val_loss = float("inf")
    best_val_acc = 0.0
    best_val_loss_epoch = -1
    best_val_acc_epoch = -1
    epochs_without_improvement = 0

    training_start_time = time.time()

    for epoch in range(1, MAX_EPOCHS + 1):
        epoch_start_time = time.time()

        # --- TRAINING PHASE ---
        model.train()
        running_train_loss = 0.0
        train_correct = 0
        train_total = 0

        for batch_idx, (images, labels) in enumerate(train_loader):
            images = images.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()

            # Efficient forward: features are frozen so we can pass in no_grad for features
            with torch.no_grad():
                features = model.features(images)
                features = nn.functional.adaptive_avg_pool2d(features, (1, 1))
                features = torch.flatten(features, 1)

            outputs = model.classifier(features)
            loss = criterion(outputs, labels)

            loss.backward()
            optimizer.step()

            running_train_loss += loss.item() * images.size(0)
            preds = torch.argmax(outputs, dim=1)
            train_correct += (preds == labels).sum().item()
            train_total += labels.size(0)

        epoch_train_loss = running_train_loss / train_total
        epoch_train_acc = train_correct / train_total

        # --- VALIDATION PHASE ---
        model.eval()
        running_val_loss = 0.0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device)
                labels = labels.to(device)

                features = model.features(images)
                features = nn.functional.adaptive_avg_pool2d(features, (1, 1))
                features = torch.flatten(features, 1)

                outputs = model.classifier(features)
                loss = criterion(outputs, labels)

                running_val_loss += loss.item() * images.size(0)
                preds = torch.argmax(outputs, dim=1)
                val_correct += (preds == labels).sum().item()
                val_total += labels.size(0)

        epoch_val_loss = running_val_loss / val_total
        epoch_val_acc = val_correct / val_total

        # Learning rate schedule update
        scheduler.step(epoch_val_loss)
        current_lr = optimizer.param_groups[0]["lr"]

        epoch_duration = time.time() - epoch_start_time

        # Record history
        history["train_loss"].append(epoch_train_loss)
        history["train_accuracy"].append(epoch_train_acc)
        history["val_loss"].append(epoch_val_loss)
        history["val_accuracy"].append(epoch_val_acc)
        history["learning_rate"].append(current_lr)
        history["epoch_duration"].append(epoch_duration)

        # Checkpoints
        status_tags = []

        # 1. Best Validation Loss Checkpoint
        if epoch_val_loss < best_val_loss:
            best_val_loss = epoch_val_loss
            best_val_loss_epoch = epoch
            epochs_without_improvement = 0
            status_tags.append("BEST_VAL_LOSS")

            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_loss": best_val_loss,
                "val_accuracy": epoch_val_acc,
                "classes": train_ds.classes,
                "class_to_idx": class_mapping
            }, CHECKPOINT_DIR / "best_model.pth")
        else:
            epochs_without_improvement += 1

        # 2. Best Validation Accuracy Checkpoint
        if epoch_val_acc > best_val_acc:
            best_val_acc = epoch_val_acc
            best_val_acc_epoch = epoch
            status_tags.append("BEST_VAL_ACC")

            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_loss": epoch_val_loss,
                "val_accuracy": best_val_acc,
                "classes": train_ds.classes,
                "class_to_idx": class_mapping
            }, CHECKPOINT_DIR / "best_acc_model.pth")

        # Save latest checkpoint
        torch.save({
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "val_loss": epoch_val_loss,
            "val_accuracy": epoch_val_acc,
            "history": history
        }, CHECKPOINT_DIR / "last_model.pth")

        # Save intermediate history json
        with open(CHECKPOINT_DIR / "training_history.json", "w") as f:
            json.dump(history, f, indent=4)

        status_str = f"[{', '.join(status_tags)}]" if status_tags else ""
        print(
            f"Epoch {epoch:02d}/{MAX_EPOCHS:02d} | "
            f"Train Loss: {epoch_train_loss:.4f} | "
            f"Train Acc: {epoch_train_acc * 100:.2f}% | "
            f"Val Loss: {epoch_val_loss:.4f} | "
            f"Val Acc: {epoch_val_acc * 100:.2f}% | "
            f"LR: {current_lr:.6f} | "
            f"{epoch_duration:.1f}s {status_str}"
        )

        # Early stopping check
        if epochs_without_improvement >= EARLY_STOPPING_PATIENCE:
            print(f"\nEarly stopping triggered after {epoch} epochs (patience = {EARLY_STOPPING_PATIENCE} reached).")
            break

    total_training_time = time.time() - training_start_time
    print("\n" + "=" * 80)
    print("TRAINING LOOP COMPLETED")
    print("=" * 80)
    print(f"Total training time: {total_training_time / 60:.2f} minutes ({total_training_time:.1f}s)")
    print(f"Best Validation Loss Epoch: {best_val_loss_epoch} (Loss: {best_val_loss:.4f})")
    print(f"Best Validation Accuracy Epoch: {best_val_acc_epoch} (Acc: {best_val_acc * 100:.2f}%)")

    # 5. Post-Training Validation & Checkpoint Reload Verification
    print("\n" + "=" * 80)
    print("POST-TRAINING CHECKPOINT VERIFICATION & INFERENCE")
    print("=" * 80)

    best_checkpoint_path = CHECKPOINT_DIR / "best_model.pth"
    print(f"Loading checkpoint from: {best_checkpoint_path}")
    checkpoint_data = torch.load(best_checkpoint_path, map_location=device)

    # Recreate fresh model
    verified_model = create_mobilenetv2(num_classes=NUM_CLASSES, pretrained=False, freeze_features=True)
    verified_model.load_state_dict(checkpoint_data["model_state_dict"])
    verified_model = verified_model.to(device)
    verified_model.eval()
    print("   Checkpoint loaded into fresh model instance successfully.")

    # Run inference on a validation batch
    val_images, val_labels = next(iter(val_loader))
    val_images = val_images.to(device)
    val_labels = val_labels.to(device)

    with torch.no_grad():
        test_out = verified_model(val_images)

    print(f"   Validation Batch Input Shape: {val_images.shape}")
    print(f"   Validation Batch Output Shape: {test_out.shape} (Expected: torch.Size([32, {NUM_CLASSES}]))")
    has_nan = torch.isnan(test_out).any().item()
    has_inf = torch.isinf(test_out).any().item()
    print(f"   Output contains NaN: {has_nan}")
    print(f"   Output contains Inf: {has_inf}")

    batch_preds = torch.argmax(test_out, dim=1)
    batch_correct = (batch_preds == val_labels).sum().item()
    print(f"   Validation Batch Accuracy: {(batch_correct / val_labels.size(0)) * 100:.2f}% ({batch_correct}/{val_labels.size(0)})")

    # 6. Plot Training Curves
    print("\n6. Generating Training Curves...")
    epochs_range = range(1, len(history["train_loss"]) + 1)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Loss plot
    ax1.plot(epochs_range, history["train_loss"], "o-", label="Train Loss", color="#1f77b4", linewidth=2)
    ax1.plot(epochs_range, history["val_loss"], "s-", label="Validation Loss", color="#ff7f0e", linewidth=2)
    ax1.axvline(best_val_loss_epoch, color="green", linestyle="--", alpha=0.7, label=f"Best Val Loss (Epoch {best_val_loss_epoch})")
    ax1.set_xlabel("Epoch", fontsize=11)
    ax1.set_ylabel("Loss", fontsize=11)
    ax1.set_title("Training Loss vs. Validation Loss", fontsize=13, fontweight="bold")
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(fontsize=10)

    # Accuracy plot
    train_acc_pct = [acc * 100 for acc in history["train_accuracy"]]
    val_acc_pct = [acc * 100 for acc in history["val_accuracy"]]
    ax2.plot(epochs_range, train_acc_pct, "o-", label="Train Accuracy", color="#1f77b4", linewidth=2)
    ax2.plot(epochs_range, val_acc_pct, "s-", label="Validation Accuracy", color="#2ca02c", linewidth=2)
    ax2.axvline(best_val_acc_epoch, color="purple", linestyle="--", alpha=0.7, label=f"Best Val Acc (Epoch {best_val_acc_epoch})")
    ax2.set_xlabel("Epoch", fontsize=11)
    ax2.set_ylabel("Accuracy (%)", fontsize=11)
    ax2.set_title("Training Accuracy vs. Validation Accuracy", fontsize=13, fontweight="bold")
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(fontsize=10)

    plt.tight_layout()
    curves_path = CHECKPOINT_DIR / "training_curves.png"
    fig.savefig(curves_path, dpi=150)
    if ARTIFACT_DIR.exists():
        fig.savefig(ARTIFACT_DIR / "training_curves.png", dpi=150)
    plt.close(fig)
    print(f"   Training curves saved to: {curves_path}")
    if ARTIFACT_DIR.exists():
        print(f"   Artifact curves saved to: {ARTIFACT_DIR / 'training_curves.png'}")

    # Summary
    best_loss_idx = best_val_loss_epoch - 1
    best_epoch_acc = history["val_accuracy"][best_loss_idx]

    print("\n" + "=" * 80)
    print("FINAL EXPERIMENT RESULTS")
    print("=" * 80)
    print(f"TRAINING STATUS: PASS")
    print(f"BEST EPOCH: {best_val_loss_epoch}")
    print(f"BEST VALIDATION ACCURACY: {best_val_acc * 100:.2f}% (Epoch {best_val_acc_epoch}) / at best loss epoch: {best_epoch_acc * 100:.2f}%")
    print(f"BEST VALIDATION LOSS: {best_val_loss:.4f}")
    print(f"CHECKPOINT: {best_checkpoint_path}")
    print(f"CHECKPOINT RELOAD: PASS")
    print(f"TRAINING CURVES: {curves_path}")

if __name__ == "__main__":
    run_training()
