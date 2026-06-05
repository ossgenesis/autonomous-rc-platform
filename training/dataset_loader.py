"""
Loads Phase 2 recorded sessions into a PyTorch Dataset.

Usage:
    from training.dataset_loader import build_loaders
    train_loader, val_loader = build_loaders("dataset/")

    # or check class balance first:
    python training/dataset_loader.py dataset/
"""

import csv
import glob
import os
import random
import sys
from collections import Counter, defaultdict
from typing import List, Tuple

import cv2
import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

# Model expects frames resized to this shape
IMG_W, IMG_H = 160, 120

CLASSES = ['w', 'a', 's', 'd', 'stop']
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}
IDX_TO_CLASS = {i: c for c, i in CLASS_TO_IDX.items()}

# Warn if any class has fewer than this many frames
MIN_FRAMES_PER_CLASS = 200


class RCDataset(Dataset):
    """PyTorch Dataset over one or more Phase 2 session directories."""

    def __init__(self, records: List[Tuple[str, int]]):
        self._records = records  # list of (frame_abs_path, class_idx)

    def __len__(self):
        return len(self._records)

    def __getitem__(self, idx):
        path, label = self._records[idx]
        frame = cv2.imread(path)
        if frame is None:
            # Return blank frame rather than crash mid-training
            frame = np.zeros((IMG_H, IMG_W, 3), dtype=np.uint8)
        frame = cv2.resize(frame, (IMG_W, IMG_H))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # HWC → CHW, normalize to [0, 1]
        tensor = torch.from_numpy(frame).permute(2, 0, 1).float() / 255.0
        return tensor, label


def _load_records(dataset_root: str) -> List[Tuple[str, int]]:
    """Walk all session subdirs, read labels.csv, return flat list of (path, label_idx)."""
    records = []
    session_dirs = sorted(glob.glob(os.path.join(dataset_root, "*")))
    for sdir in session_dirs:
        labels_csv = os.path.join(sdir, "labels.csv")
        frames_dir = os.path.join(sdir, "frames")
        if not os.path.exists(labels_csv):
            continue
        with open(labels_csv, newline="") as f:
            for row in csv.DictReader(f):
                cmd = row.get("command", "stop").strip()
                # Map diagonal combos to their dominant direction instead of discarding
                if cmd not in CLASS_TO_IDX:
                    cmd = cmd.split("+")[0] if "+" in cmd and cmd.split("+")[0] in CLASS_TO_IDX else "stop"
                frame_path = os.path.join(frames_dir, row["frame_file"])
                if os.path.exists(frame_path):
                    records.append((frame_path, CLASS_TO_IDX[cmd]))
    return records


def _print_class_report(records: List[Tuple[str, int]]):
    counts = Counter(label for _, label in records)
    total = len(records)
    print(f"\n{'─'*45}")
    print(f"  Dataset: {total} frames across {len(CLASSES)} classes")
    print(f"{'─'*45}")
    any_low = False
    for idx, cls in IDX_TO_CLASS.items():
        n = counts.get(idx, 0)
        bar = '█' * min(30, n // 20)
        warn = '  ⚠ LOW' if n < MIN_FRAMES_PER_CLASS else ''
        print(f"  [{idx}] {cls:>5}  {n:>5} frames  {bar}{warn}")
        if n < MIN_FRAMES_PER_CLASS:
            any_low = True
    print(f"{'─'*45}\n")
    if any_low:
        print("  Some classes are under-collected. Drive more sessions")
        print("  with deliberate turning/stopping before training.\n")


def _make_weighted_sampler(records: List[Tuple[str, int]]) -> WeightedRandomSampler:
    """Up-sample rare classes so each batch sees a balanced mix."""
    counts = Counter(label for _, label in records)
    class_weights = {idx: 1.0 / max(counts[idx], 1) for idx in range(len(CLASSES))}
    sample_weights = [class_weights[label] for _, label in records]
    return WeightedRandomSampler(
        weights=sample_weights,
        num_samples=len(sample_weights),
        replacement=True,
    )


def build_loaders(
    dataset_root: str = "dataset/",
    val_split: float = 0.2,
    batch_size: int = 32,
    num_workers: int = 2,
    print_report: bool = True,
) -> Tuple[DataLoader, DataLoader, Counter]:
    """Return (train_loader, val_loader) ready for training."""
    records = _load_records(dataset_root)
    if not records:
        raise RuntimeError(
            f"No labelled frames found under '{dataset_root}'. "
            "Record a Phase 2 session first (press R in telemetry_app.py)."
        )

    if print_report:
        _print_class_report(records)

    # Stratified random split: each class contributes val_split fraction to val
    by_class = defaultdict(list)
    for rec in records:
        by_class[rec[1]].append(rec)
    rng = random.Random(42)
    train_records, val_records = [], []
    for recs in by_class.values():
        rng.shuffle(recs)
        n_val = max(1, int(len(recs) * val_split))
        val_records.extend(recs[:n_val])
        train_records.extend(recs[n_val:])

    train_ds = RCDataset(train_records)
    val_ds   = RCDataset(val_records)

    sampler = _make_weighted_sampler(train_records)

    train_loader = DataLoader(
        train_ds, batch_size=batch_size,
        sampler=sampler, num_workers=num_workers, pin_memory=True,
    )
    val_loader = DataLoader(
        val_ds, batch_size=batch_size,
        shuffle=False, num_workers=num_workers, pin_memory=True,
    )
    train_counts = Counter(label for _, label in train_records)
    return train_loader, val_loader, train_counts


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "dataset/"
    records = _load_records(root)
    _print_class_report(records)
