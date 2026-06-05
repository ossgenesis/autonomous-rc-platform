"""
Evaluate SteerNet and generate training curves and a confusion matrix.
Saves outputs to models/eval/

Usage:
    python training/evaluate.py
    python training/evaluate.py --dataset dataset/ --model models/steer_net.pt
"""

import argparse
import os
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import torch
import numpy as np
from sklearn.metrics import confusion_matrix

from training.dataset_loader import build_loaders, CLASSES
from training.model import load_model

def plot_curves(log_path, out_dir):
    if not os.path.exists(log_path):
        print(f"Log file not found: {log_path}. Skip plotting curves.")
        return
    df = pd.read_csv(log_path)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Loss
    ax1.plot(df['epoch'], df['train_loss'], label='Train Loss')
    ax1.plot(df['epoch'], df['val_loss'], label='Val Loss')
    ax1.set_title('Training and Validation Loss')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss')
    ax1.legend()
    
    # Accuracy
    ax2.plot(df['epoch'], df['train_acc'], label='Train Acc')
    ax2.plot(df['epoch'], df['val_acc'], label='Val Acc')
    ax2.set_title('Training and Validation Accuracy')
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Accuracy')
    ax2.legend()
    
    out_path = os.path.join(out_dir, "curves.png")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    print(f"Saved curves to {out_path}")

def plot_confusion_matrix(model_path, dataset_root, out_dir):
    if not os.path.exists(model_path):
        print(f"Model file not found: {model_path}. Skip confusion matrix.")
        return
    
    device = torch.device("mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading model on {device}...")
    model = load_model(model_path, device)
    
    print(f"Loading validation dataset from {dataset_root}...")
    try:
        _, val_loader, _ = build_loaders(dataset_root, print_report=False)
    except RuntimeError as e:
        print(f"Failed to load dataset: {e}")
        return

    model.eval()
    all_preds = []
    all_labels = []
    
    print("Evaluating...")
    with torch.no_grad():
        for frames, labels in val_loader:
            frames = frames.to(device)
            logits = model(frames)
            preds = logits.argmax(dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_labels.extend(labels.numpy())
            
    cm = confusion_matrix(all_labels, all_preds, labels=list(range(len(CLASSES))))
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=CLASSES, yticklabels=CLASSES)
    plt.title('Confusion Matrix')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    
    out_path = os.path.join(out_dir, "confusion_matrix.png")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    print(f"Saved confusion matrix to {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="dataset/")
    parser.add_argument("--model", default="models/steer_net.pt")
    parser.add_argument("--log", default="models/train_log.csv")
    parser.add_argument("--out", default="models/eval/")
    args = parser.parse_args()
    
    os.makedirs(args.out, exist_ok=True)
    plot_curves(args.log, args.out)
    plot_confusion_matrix(args.model, args.dataset, args.out)
