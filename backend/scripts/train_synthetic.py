"""Trains a BASELINE classifier on synthetic transit views so the pipeline runs end to end.
For science use, retrain on labelled Kepler DR25 / TESS TOI data (same input views, same model)."""
import os

import numpy as np
import torch
import torch.nn as nn

from app.services.model import ExoCNN
from app.services.preprocess import norm_view

rng = np.random.default_rng(7)
XG, XL = np.linspace(-0.5, 0.5, 201), np.linspace(-3, 3, 61)


def dip(u, depth, ing):
    return depth * np.clip((0.5 - np.abs(u)) / ing, 0, 1)


def sample(label):
    d = rng.uniform(0.004, 0.06)  # transit duration as a fraction of the period
    snr = rng.uniform(3, 30)
    depth = 1.0
    ing = rng.uniform(0.1, 0.3)
    kind = "planet" if label else rng.choice(["noise", "sine", "eb"])
    g = np.zeros(201)
    l = np.zeros(61)
    if kind == "planet":
        g -= dip(XG / d, depth, ing)
        l -= dip(XL, depth, ing)
    elif kind == "eb":  # deep V-shape plus a secondary eclipse
        g -= dip(XG / d, depth, 0.5) + 0.5 * dip((np.abs(XG) - 0.5) / d, depth, 0.5)
        l -= dip(XL, depth, 0.5)
    elif kind == "sine":
        a, p = rng.uniform(0.3, 1), rng.uniform(0.5, 3)
        g += a * np.sin(2 * np.pi * (XG * p + rng.random()))
        l += a * np.sin(2 * np.pi * (XL / 6 * p + rng.random()))
    scale = (1 / snr) if kind != "eb" else (1 / rng.uniform(15, 80))
    g += rng.normal(0, scale, 201)
    l += rng.normal(0, scale * 1.5, 61)
    return norm_view(g).astype("float32"), norm_view(l).astype("float32")


def batch(n):
    y = rng.integers(0, 2, n)
    s = [sample(int(i)) for i in y]
    return (torch.tensor(np.stack([a for a, _ in s]))[:, None], torch.tensor(np.stack([b for _, b in s]))[:, None],
            torch.tensor(y, dtype=torch.float32)[:, None])


if __name__ == "__main__":
    torch.manual_seed(7)
    net, loss_fn = ExoCNN(), nn.BCEWithLogitsLoss()
    opt = torch.optim.Adam(net.parameters(), 1e-3)
    G, L, Y = batch(6000)
    for epoch in range(20):
        net.train()
        for i in torch.randperm(len(Y)).split(128):
            opt.zero_grad()
            loss_fn(net(G[i], L[i]), Y[i]).backward()
            opt.step()
    net.eval()
    G2, L2, Y2 = batch(1000)
    with torch.no_grad():
        acc = ((torch.sigmoid(net(G2, L2)) > 0.5).float() == Y2).float().mean().item()
    print(f"synthetic holdout accuracy: {acc:.3f}")
    os.makedirs("weights", exist_ok=True)
    torch.save({"state": net.state_dict(), "trained_on": "synthetic transits (baseline)"}, "weights/exo_cnn.pt")
