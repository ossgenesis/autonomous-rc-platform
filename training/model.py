"""
SteerNet — lightweight CNN for RC car steering command classification.

Input:  (B, 3, 120, 160)  RGB frame, normalised to [0, 1]
Output: (B, 5)            raw logits for [w, a, s, d, stop]

Designed to run at 30+ FPS on MacBook CPU inference.
"""

import torch
import torch.nn as nn

from training.dataset_loader import CLASSES, IMG_H, IMG_W


class SteerNet(nn.Module):
    def __init__(self, num_classes: int = len(CLASSES), dropout: float = 0.4):
        super().__init__()

        self.features = nn.Sequential(
            # Block 1: 160×120 → 78×58
            nn.Conv2d(3, 16, kernel_size=5, padding=2),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),

            # Block 2: 78×58 → 38×28
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),

            # Block 3: 38×28 → 18×13
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
        )

        # Compute flattened size without hard-coding it
        with torch.no_grad():
            _dummy = torch.zeros(1, 3, IMG_H, IMG_W)
            flat = self.features(_dummy).flatten(1).shape[1]

        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(flat, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(256, 64),
            nn.ReLU(inplace=True),
            nn.Linear(64, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(x))


def load_model(checkpoint_path: str, device: torch.device) -> SteerNet:
    model = SteerNet()
    state = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(state["model"])
    model.to(device)
    model.eval()
    return model


if __name__ == "__main__":
    model = SteerNet()
    dummy = torch.randn(1, 3, IMG_H, IMG_W)
    out = model(dummy)
    params = sum(p.numel() for p in model.parameters())
    print(f"Output shape : {out.shape}  (expected: [1, {len(CLASSES)}])")
    print(f"Parameters   : {params:,}")
