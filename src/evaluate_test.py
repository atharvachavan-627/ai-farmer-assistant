"""
Final evaluation script on the held-out TEST dataset for AI Farmer Assistant.

Loads best checkpoint from models/mobilenetv2/best_model.pth, runs inference on test split,
and calculates comprehensive classification metrics.
"""

import sys
import json
import time
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import torch
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dataset import get_datasets, get_dataloaders
from src.model import create_mobilenetv2

CHECKPOINT_DIR = PROJECT_ROOT / "models" / "mobilenetv2"
ARTIFACT_DIR = Path(r"C:\Users\ATHARVA\.gemini\antigravity-ide\brain\ba4ca457-3323-47ea-936e-1a18b12fd977")


def evaluate_test_set():
    print("=" * 80)
    print("FINAL HELD-OUT TEST EVALUATION")
    print("=" * 80)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # 1. Load Test Dataset & DataLoader
    print("\n1. Loading test dataset...")
    train_ds, val_ds, test_ds = get_datasets()
    class_names = test_ds.classes
    num_classes = len(class_names)
    print(f"   Test samples: {len(test_ds)}")
    print(f"   Classes: {num_classes}")

    _, _, test_loader = get_dataloaders(
        train_ds, val_ds, test_ds,
        batch_size=32,
        num_workers=0
    )

    # 2. Load Best Checkpoint
    checkpoint_path = CHECKPOINT_DIR / "best_model.pth"
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found at: {checkpoint_path}")

    print(f"\n2. Loading best checkpoint: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location=device)
    print(f"   Checkpoint saved at epoch: {checkpoint.get('epoch', 'N/A')}")
    print(f"   Checkpoint validation loss: {checkpoint.get('val_loss', 'N/A')}")
    print(f"   Checkpoint validation accuracy: {checkpoint.get('val_accuracy', 'N/A')}")

    model = create_mobilenetv2(num_classes=num_classes, pretrained=False, freeze_features=True)
    model.load_state_dict(checkpoint["model_state_dict"])
    model = model.to(device)
    model.eval()

    # 3. Run Inference on Test Set
    print("\n3. Running test set inference...")
    y_true = []
    y_pred = []
    
    t0 = time.time()
    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device)
            outputs = model(images)
            preds = torch.argmax(outputs, dim=1)

            y_true.extend(labels.cpu().numpy())
            y_pred.extend(preds.cpu().numpy())

    inference_time = time.time() - t0
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    print(f"   Inference completed in {inference_time:.2f}s ({len(y_true) / inference_time:.1f} samples/sec)")

    # 4. Metric Calculations
    test_acc = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    weighted_f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)

    per_class_precision = precision_score(y_true, y_pred, average=None, zero_division=0)
    per_class_recall = recall_score(y_true, y_pred, average=None, zero_division=0)
    per_class_f1 = f1_score(y_true, y_pred, average=None, zero_division=0)
    
    cm = confusion_matrix(y_true, y_pred, labels=np.arange(num_classes))
    report_text = classification_report(y_true, y_pred, target_names=class_names, digits=4, zero_division=0)

    total_samples = len(y_true)
    correct_count = int(np.sum(y_true == y_pred))
    incorrect_count = int(total_samples - correct_count)

    # 5. Identify Strongest, Weakest, and Major Confusion Pairs
    per_class_summary = []
    for idx, cname in enumerate(class_names):
        per_class_summary.append({
            "class_index": idx,
            "class_name": cname,
            "precision": float(per_class_precision[idx]),
            "recall": float(per_class_recall[idx]),
            "f1_score": float(per_class_f1[idx]),
            "support": int(np.sum(y_true == idx))
        })

    sorted_by_f1 = sorted(per_class_summary, key=lambda x: x["f1_score"], reverse=True)
    best_classes = sorted_by_f1[:3]
    weakest_classes = sorted_by_f1[-3:]

    # Major confusion pairs (off-diagonal)
    confusion_pairs = []
    for i in range(num_classes):
        for j in range(num_classes):
            if i != j and cm[i, j] > 0:
                confusion_pairs.append({
                    "true_class": class_names[i],
                    "predicted_class": class_names[j],
                    "count": int(cm[i, j]),
                    "true_class_support": int(np.sum(y_true == i)),
                    "error_percentage": float(cm[i, j] / np.sum(y_true == i) * 100)
                })

    confusion_pairs.sort(key=lambda x: x["count"], reverse=True)
    major_confusions = confusion_pairs[:5]

    # 6. Save results to JSON
    results_dict = {
        "test_accuracy": float(test_acc),
        "macro_f1": float(macro_f1),
        "weighted_f1": float(weighted_f1),
        "total_samples": total_samples,
        "correct_predictions": correct_count,
        "incorrect_predictions": incorrect_count,
        "best_classes": best_classes,
        "weakest_classes": weakest_classes,
        "major_confusions": major_confusions,
        "per_class_metrics": per_class_summary,
        "confusion_matrix": cm.tolist(),
        "classification_report": report_text
    }

    results_file = CHECKPOINT_DIR / "test_evaluation_results.json"
    with open(results_file, "w") as f:
        json.dump(results_dict, f, indent=4)
    print(f"\n4. Test evaluation results saved to: {results_file}")

    # 7. Plot and Save Confusion Matrix
    print("\n5. Plotting Confusion Matrix...")
    fig, ax = plt.subplots(figsize=(12, 10))
    im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    ax.set(
        xticks=np.arange(num_classes),
        yticks=np.arange(num_classes),
        xticklabels=class_names,
        yticklabels=class_names,
        title=f"Test Set Confusion Matrix (Accuracy: {test_acc * 100:.2f}%, Macro F1: {macro_f1 * 100:.2f}%)",
        ylabel="True Disease Label",
        xlabel="Predicted Disease Label"
    )

    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor", fontsize=9)
    plt.setp(ax.get_yticklabels(), fontsize=9)

    thresh = cm.max() / 2.0
    for i in range(num_classes):
        for j in range(num_classes):
            val = cm[i, j]
            color = "white" if val > thresh else "black"
            ax.text(j, i, format(val, "d"), ha="center", va="center", color=color, fontsize=8)

    plt.tight_layout()
    cm_path = CHECKPOINT_DIR / "test_confusion_matrix.png"
    fig.savefig(cm_path, dpi=150)
    if ARTIFACT_DIR.exists():
        fig.savefig(ARTIFACT_DIR / "test_confusion_matrix.png", dpi=150)
    plt.close(fig)
    print(f"   Confusion matrix image saved to: {cm_path}")
    if ARTIFACT_DIR.exists():
        print(f"   Artifact confusion matrix saved to: {ARTIFACT_DIR / 'test_confusion_matrix.png'}")

    # 8. Print Formatted Report
    print("\n" + "=" * 80)
    print(f"TEST EVALUATION STATUS: PASS")
    print("=" * 80)
    print(f"TEST ACCURACY: {test_acc * 100:.2f}% ({correct_count}/{total_samples} correct, {incorrect_count} incorrect)")
    print(f"MACRO F1: {macro_f1 * 100:.2f}%")
    print(f"WEIGHTED F1: {weighted_f1 * 100:.2f}%")

    print("\nBEST CLASSES:")
    for c in best_classes:
        print(f" - {c['class_name']}: F1 = {c['f1_score'] * 100:.2f}% (P={c['precision'] * 100:.2f}%, R={c['recall'] * 100:.2f}%, Support={c['support']})")

    print("\nWEAKEST CLASSES:")
    for c in weakest_classes:
        print(f" - {c['class_name']}: F1 = {c['f1_score'] * 100:.2f}% (P={c['precision'] * 100:.2f}%, R={c['recall'] * 100:.2f}%, Support={c['support']})")

    print("\nMAJOR CONFUSIONS:")
    for p in major_confusions:
        print(f" - True: {p['true_class']} -> Predicted: {p['predicted_class']} ({p['count']} errors / {p['true_class_support']}, {p['error_percentage']:.2f}%)")

    print("\nCONFUSION MATRIX:")
    print(cm)

    print("\nCLASSIFICATION REPORT:")
    print(report_text)

if __name__ == "__main__":
    evaluate_test_set()
