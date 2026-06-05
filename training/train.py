"""
Train SteerNet on Phase 2 collected data.

Usage:
    python training/train.py
    python training/train.py --dataset dataset/ --epochs 30 --batch 32
    python training/train.py --resume models/steer_net.pt

Saves best checkpoint to models/steer_net.pt
Saves training log to models/train_log.csv  (for Gemini's evaluate.py plots)
"""

import argparse
import csv
import os
import time
from typing import Optional

import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR

from training.dataset_loader import CLASSES, build_loaders
from training.model import SteerNet, load_model


def _pick_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def train(
    dataset_root: str = "dataset/",
    epochs: int = 30,
    batch_size: int = 32,
    lr: float = 1e-3,
    resume: Optional[str] = None,
    out_dir: str = "models/",
):
    device = _pick_device()
    print(f"Device: {device}")

    train_loader, val_loader, train_counts = build_loaders(
        dataset_root, batch_size=batch_size, print_report=True
    )

    model = SteerNet().to(device)
    start_epoch = 0
    best_val_acc = 0.0

    if resume and os.path.exists(resume):
        ckpt = torch.load(resume, map_location=device)
        model.load_state_dict(ckpt["model"])
        start_epoch = ckpt.get("epoch", 0) + 1
        best_val_acc = ckpt.get("val_acc", 0.0)
        print(f"Resumed from {resume} (epoch {start_epoch}, best val acc {best_val_acc:.1%})")

    # Weight each class inversely by its frequency so rare steering commands matter as much as stop
    total = sum(train_counts.values())
    class_weights = torch.tensor(
        [total / max(train_counts[i], 1) for i in range(len(CLASSES))],
        dtype=torch.float32, device=device,
    )
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = CosineAnnealingLR(optimizer, T_max=epochs)

    os.makedirs(out_dir, exist_ok=True)
    log_path = os.path.join(out_dir, "train_log.csv")
    log_exists = os.path.exists(log_path) and resume

    with open(log_path, "a" if log_exists else "w", newline="") as log_f:
        log_writer = csv.writer(log_f)
        if not log_exists:
            log_writer.writerow(["epoch", "train_loss", "train_acc", "val_loss", "val_acc", "lr"])

        for epoch in range(start_epoch, start_epoch + epochs):
            # ── Train ──────────────────────────────────────────────────────
            model.train()
            t0 = time.time()
            train_loss, train_correct, train_total = 0.0, 0, 0

            for frames, labels in train_loader:
                frames, labels = frames.to(device), labels.to(device)
                optimizer.zero_grad()
                logits = model(frames)
                loss = criterion(logits, labels)
                loss.backward()
                optimizer.step()

                train_loss += loss.item() * len(labels)
                train_correct += (logits.argmax(1) == labels).sum().item()
                train_total += len(labels)

            train_loss /= train_total
            train_acc = train_correct / train_total

            # ── Validate ───────────────────────────────────────────────────
            model.eval()
            val_loss, val_correct, val_total = 0.0, 0, 0

            with torch.no_grad():
                for frames, labels in val_loader:
                    frames, labels = frames.to(device), labels.to(device)
                    logits = model(frames)
                    loss = criterion(logits, labels)
                    val_loss += loss.item() * len(labels)
                    val_correct += (logits.argmax(1) == labels).sum().item()
                    val_total += len(labels)

            val_loss /= val_total
            val_acc = val_correct / val_total
            current_lr = scheduler.get_last_lr()[0]
            elapsed = time.time() - t0

            print(
                f"Epoch {epoch+1:3d}/{start_epoch+epochs}  "
                f"train {train_acc:.1%} ({train_loss:.4f})  "
                f"val {val_acc:.1%} ({val_loss:.4f})  "
                f"lr {current_lr:.2e}  {elapsed:.1f}s"
            )

            log_writer.writerow([epoch + 1, f"{train_loss:.6f}", f"{train_acc:.6f}",
                                  f"{val_loss:.6f}", f"{val_acc:.6f}", f"{current_lr:.8f}"])
            log_f.flush()

            # Save best checkpoint
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                ckpt_path = os.path.join(out_dir, "steer_net.pt")
                torch.save({
                    "model": model.state_dict(),
                    "epoch": epoch,
                    "val_acc": val_acc,
                    "classes": CLASSES,
                }, ckpt_path)
                print(f"  ✓ Saved best checkpoint → {ckpt_path}  (val acc {val_acc:.1%})")

            scheduler.step()

    print(f"\nTraining complete. Best val accuracy: {best_val_acc:.1%}")
    print(f"Checkpoint: {os.path.join(out_dir, 'steer_net.pt')}")
    print(f"Log: {log_path}  (run training/evaluate.py to plot)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train SteerNet on Phase 2 data")
    parser.add_argument("--dataset", default="dataset/", help="Dataset root directory")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--resume", default=None, help="Path to checkpoint to resume from")
    parser.add_argument("--out", default="models/", help="Output directory for checkpoints")
    args = parser.parse_args()

    train(
        dataset_root=args.dataset,
        epochs=args.epochs,
        batch_size=args.batch,
        lr=args.lr,
        resume=args.resume,
        out_dir=args.out,
    )
