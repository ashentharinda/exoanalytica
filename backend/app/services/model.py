import os

import numpy as np
import torch
import torch.nn as nn


def _block(i, o):
    return [nn.Conv1d(i, o, 5, padding=2), nn.BatchNorm1d(o), nn.ReLU(), nn.MaxPool1d(2)]


class ExoCNN(nn.Module):
    """Two-branch 1D CNN: global (201 bins, whole orbit) + local (61 bins, around the transit)."""

    def __init__(self):
        super().__init__()
        self.g = nn.Sequential(*_block(1, 16), *_block(16, 32), *_block(32, 64), nn.AdaptiveAvgPool1d(4), nn.Flatten())
        self.l = nn.Sequential(*_block(1, 16), *_block(16, 32), nn.AdaptiveAvgPool1d(4), nn.Flatten())
        self.head = nn.Sequential(nn.Linear(384, 64), nn.ReLU(), nn.Dropout(0.3), nn.Linear(64, 1))

    def forward(self, g, l):
        return self.head(torch.cat([self.g(g), self.l(l)], 1))


_CACHE = {}


def _net():
    if "net" not in _CACHE:
        path = os.environ.get("MODEL_PATH", "")
        if path and os.path.exists(path):
            ckpt = torch.load(path, map_location="cpu", weights_only=True)
            net = ExoCNN()
            net.load_state_dict(ckpt["state"])
            net.eval()
            _CACHE["net"] = (net, ckpt.get("trained_on", "unknown"))
        else:
            _CACHE["net"] = (None, None)
    return _CACHE["net"]


def _heuristic(snr):
    return float(1 / (1 + np.exp(-(snr - 8) / 2)))


def classify(g, l, snr):
    """Returns (score 0-1, method, trained_on)."""
    net, trained_on = _net()
    if net is None:
        return _heuristic(snr), "bls-snr-heuristic", None
    with torch.no_grad():
        p = torch.sigmoid(net(torch.from_numpy(g)[None, None], torch.from_numpy(l)[None, None]))
    return float(p[0, 0]), "cnn", trained_on


def classify_locals(g, locals_, snrs):
    """Score each individual transit: shared global view + that transit's own local view."""
    if not locals_:
        return []
    net, _ = _net()
    if net is None:
        return [_heuristic(s) for s in snrs]
    G = torch.from_numpy(g)[None, None].repeat(len(locals_), 1, 1)
    L = torch.from_numpy(np.stack(locals_))[:, None]
    with torch.no_grad():
        return torch.sigmoid(net(G, L))[:, 0].tolist()