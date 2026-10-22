"""
Training and evaluation script for Dedicated Crop & Plant Validator Model.

Builds a 4-class classifier on top of MobileNetV2 feature embeddings:
Classes:
0: tomato (Tomato foliar leaves across all 10 conditions)
1: potato (Potato foliar leaves across all 3 conditions)
2: unsupported_plant (Leaves from Apple, Corn, Grape, Peach, Pepper, Strawberry, Cherry, Blueberry, Orange, Soybean, Squash)
3: non_plant (Non-plant images: faces/people, vehicles, objects, buildings, animals, fruits/vegetables without leaves, text/graphics)
"""

import os
import random
import time
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
from PIL import Image, ImageDraw
from torchvision.models import mobilenet_v2, MobileNet_V2_Weights
from torchvision import transforms

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PV_COLOR_DIR = PROJECT_ROOT / "data" / "raw" / "plantvillage" / "plantvillage dataset" / "color"
OUTPUT_MODEL_DIR = PROJECT_ROOT / "models" / "crop_validator"
OUTPUT_MODEL_DIR.mkdir(parents=True, exist_ok=True)

# Image preprocessing matching MobileNetV2 standard
val_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

def generate_synthetic_non_plants(count=150):
    """
    Generates diverse non-plant images (skin tones/portraits, vehicles/shapes,
    text/documents, indoor rooms, fruits without leaves, solid patterns).
    """
    images = []
    for i in range(count):
        mode = i % 6
        img = Image.new("RGB", (224, 224), (240, 240, 240))
        draw = ImageDraw.Draw(img)

        if mode == 0:
            # Human face / skin tone synthetic
            skin_color = (random.randint(180, 255), random.randint(140, 210), random.randint(110, 180))
            draw.ellipse([50, 40, 174, 180], fill=skin_color)
            # Eyes and mouth
            draw.ellipse([75, 80, 95, 95], fill=(50, 30, 20))
            draw.ellipse([129, 80, 149, 95], fill=(50, 30, 20))
            draw.rectangle([85, 140, 139, 155], fill=(180, 50, 50))
        elif mode == 1:
            # Vehicle / building shapes (rectangles, grays, metallics, blue sky)
            draw.rectangle([0, 0, 224, 112], fill=(135, 206, 235)) # sky
            draw.rectangle([0, 112, 224, 224], fill=(80, 80, 80))  # road
            draw.rectangle([40, 100, 184, 180], fill=(random.randint(50, 220), 20, 20)) # car body
            draw.ellipse([60, 160, 90, 190], fill=(10, 10, 10))    # wheel
            draw.ellipse([134, 160, 164, 190], fill=(10, 10, 10))  # wheel
        elif mode == 2:
            # Document / screenshot / text
            draw.rectangle([20, 20, 204, 204], fill=(255, 255, 255), outline=(180, 180, 180))
            for y in range(40, 180, 14):
                draw.line([(40, y), (random.randint(120, 180), y)], fill=(40, 40, 40), width=2)
        elif mode == 3:
            # Tomato fruit / apple fruit alone without leaves (circular red object)
            fruit_color = (random.randint(200, 240), random.randint(20, 50), random.randint(20, 40))
            draw.rectangle([0, 0, 224, 224], fill=(210, 205, 195)) # table background
            draw.ellipse([45, 45, 179, 179], fill=fruit_color)     # round fruit
            draw.ellipse([105, 38, 119, 52], fill=(110, 60, 30))   # small brown stem nub
        elif mode == 4:
            # Animal / fur synthetic patterns (browns, tans, stripes)
            base_fur = (random.randint(120, 180), random.randint(80, 140), random.randint(40, 80))
            draw.rectangle([0, 0, 224, 224], fill=base_fur)
            for j in range(15):
                draw.line([(random.randint(0, 224), 0), (random.randint(0, 224), 224)], fill=(40, 25, 15), width=random.randint(4, 10))
        else:
            # Furniture / indoor room (wood browns, tiles, walls)
            draw.rectangle([0, 0, 224, 120], fill=(220, 215, 200)) # wall
            draw.rectangle([0, 120, 224, 224], fill=(139, 90, 43)) # wooden floor
            draw.rectangle([50, 80, 170, 180], fill=(70, 50, 35))  # furniture block

        images.append(img)
    return images


def load_dataset():
    """Loads balanced image paths and labels."""
    all_classes = os.listdir(PV_COLOR_DIR)
    tomato_dirs = [c for c in all_classes if c.startswith("Tomato___")]
    potato_dirs = [c for c in all_classes if c.startswith("Potato___")]
    other_dirs = [c for c in all_classes if not c.startswith("Tomato___") and not c.startswith("Potato___")]

    samples = [] # (image_path_or_PIL, label_id)
    # 0: tomato, 1: potato, 2: unsupported_plant, 3: non_plant

    # 1. Tomato samples (~800)
    for d in tomato_dirs:
        folder = PV_COLOR_DIR / d
        files = [f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.png'))]
        random.shuffle(files)
        for f in files[:80]:
            samples.append((folder / f, 0))

    # 2. Potato samples (~600)
    for d in potato_dirs:
        folder = PV_COLOR_DIR / d
        files = [f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.png'))]
        random.shuffle(files)
        for f in files[:200]:
            samples.append((folder / f, 1))

    # 3. Unsupported plant samples (~625)
    for d in other_dirs:
        folder = PV_COLOR_DIR / d
        files = [f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.png'))]
        random.shuffle(files)
        for f in files[:25]:
            samples.append((folder / f, 2))

    # 4. Non-plant samples (220)
    synthetic_non_plants = generate_synthetic_non_plants(220)
    for img in synthetic_non_plants:
        samples.append((img, 3))

    random.shuffle(samples)
    print(f"Total sampled dataset: {len(samples)} images")
    label_counts = {0: 0, 1: 0, 2: 0, 3: 0}
    for _, l in samples:
        label_counts[l] += 1
    print(f"Counts per class: Tomato(0): {label_counts[0]}, Potato(1): {label_counts[1]}, Unsupported(2): {label_counts[2]}, Non-Plant(3): {label_counts[3]}")
    return samples


def main():
    print("Loading MobileNetV2 pretrained feature extractor...")
    weights = MobileNet_V2_Weights.DEFAULT
    mobilenet = mobilenet_v2(weights=weights)
    mobilenet.eval()
    feature_extractor = mobilenet.features

    samples = load_dataset()

    # Split 80% train, 20% test
    split_idx = int(0.8 * len(samples))
    train_samples = samples[:split_idx]
    test_samples = samples[split_idx:]

    print(f"Train set: {len(train_samples)}, Test set: {len(test_samples)}")

    def extract_features(sample_list):
        features_list = []
        labels_list = []
        batch_tensors = []
        batch_labels = []

        for item, label in sample_list:
            if isinstance(item, (str, Path)):
                img = Image.open(item).convert("RGB")
            else:
                img = item.convert("RGB")
            tensor = val_transforms(img)
            batch_tensors.append(tensor)
            batch_labels.append(label)

            if len(batch_tensors) >= 32:
                b_t = torch.stack(batch_tensors)
                with torch.no_grad():
                    f = feature_extractor(b_t)
                    pooled = torch.nn.functional.adaptive_avg_pool2d(f, (1, 1)).flatten(1)
                features_list.append(pooled)
                labels_list.extend(batch_labels)
                batch_tensors = []
                batch_labels = []

        if batch_tensors:
            b_t = torch.stack(batch_tensors)
            with torch.no_grad():
                f = feature_extractor(b_t)
                pooled = torch.nn.functional.adaptive_avg_pool2d(f, (1, 1)).flatten(1)
            features_list.append(pooled)
            labels_list.extend(batch_labels)

        X = torch.cat(features_list, dim=0)
        y = torch.tensor(labels_list, dtype=torch.long)
        return X, y

    print("Extracting train features...")
    t0 = time.time()
    X_train, y_train = extract_features(train_samples)
    print(f"Train features extracted: shape {X_train.shape} in {time.time()-t0:.2f}s")

    print("Extracting test features...")
    t0 = time.time()
    X_test, y_test = extract_features(test_samples)
    print(f"Test features extracted: shape {X_test.shape} in {time.time()-t0:.2f}s")

    # Define PyTorch Linear Crop Classifier
    class CropClassifier(nn.Module):
        def __init__(self, in_features=1280, num_classes=4):
            super().__init__()
            self.linear = nn.Linear(in_features, num_classes)

        def forward(self, x):
            return self.linear(x)

    model = CropClassifier(in_features=1280, num_classes=4)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.005, weight_decay=1e-4)

    # Train linear model for 60 epochs
    print("Training CropClassifier linear head...")
    model.train()
    for epoch in range(60):
        optimizer.zero_grad()
        logits = model(X_train)
        loss = criterion(logits, y_train)
        loss.backward()
        optimizer.step()

    # Evaluate on test set
    model.eval()
    with torch.no_grad():
        test_logits = model(X_test)
        test_preds = torch.argmax(test_logits, dim=1)
        acc = (test_preds == y_test).float().mean().item()
        print(f"\n>>> HELD-OUT TEST ACCURACY: {acc * 100:.2f}% <<<")

        # Per-class accuracy
        class_names = ["tomato", "potato", "unsupported_plant", "non_plant"]
        for cid, cname in enumerate(class_names):
            mask = (y_test == cid)
            if mask.sum() > 0:
                c_acc = (test_preds[mask] == y_test[mask]).float().mean().item()
                print(f"  Class '{cname}' accuracy: {c_acc * 100:.2f}% ({mask.sum().item()} test samples)")

    # Save model weights and metadata
    save_path = OUTPUT_MODEL_DIR / "crop_validator_head.pth"
    torch.save({
        "state_dict": model.state_dict(),
        "classes": class_names,
        "in_features": 1280,
        "num_classes": 4,
        "test_accuracy": acc,
        "trained_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }, save_path)
    print(f"\nModel saved successfully to: {save_path}")

if __name__ == "__main__":
    main()
