"""Confidence calibration analysis.

The model's softmax output is treated as a probability. But "this is team X
with probability 0.7" is only meaningful if the model is right 70% of the
time when it says 0.7. That's *calibration*, and it's the difference between
a confidence score that's usable for prioritization vs. one that's just
decoration.

We bin predictions by confidence (0.0-0.1, 0.1-0.2, ..., 0.9-1.0) and
compare empirical accuracy in each bin. The Expected Calibration Error
(ECE) summarizes the gap.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class CalibrationBin:
    low: float
    high: float
    n: int
    mean_confidence: float
    accuracy: float


@dataclass
class CalibrationResult:
    bins: list[CalibrationBin]
    ece: float          # expected calibration error (lower is better; perfect=0)
    overall_acc: float
    overall_conf: float


def calibration_curve(predictions: np.ndarray, confidences: np.ndarray,
                      y_true: np.ndarray, mask: np.ndarray | None = None,
                      n_bins: int = 10) -> CalibrationResult:
    if mask is None:
        mask = np.ones_like(predictions, dtype=bool)
    p = predictions[mask]
    c = confidences[mask]
    y = y_true[mask]

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins: list[CalibrationBin] = []
    ece = 0.0
    n_total = len(p) or 1

    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        in_bin = (c >= lo) & (c < (hi if i < n_bins - 1 else hi + 1e-9))
        n = int(in_bin.sum())
        if n == 0:
            bins.append(CalibrationBin(low=lo, high=hi, n=0,
                                       mean_confidence=float("nan"),
                                       accuracy=float("nan")))
            continue
        mean_conf = float(c[in_bin].mean())
        acc = float((p[in_bin] == y[in_bin]).mean())
        bins.append(CalibrationBin(low=lo, high=hi, n=n,
                                   mean_confidence=mean_conf, accuracy=acc))
        ece += abs(mean_conf - acc) * n / n_total

    return CalibrationResult(
        bins=bins, ece=float(ece),
        overall_acc=float((p == y).mean()) if len(p) else 0.0,
        overall_conf=float(c.mean()) if len(c) else 0.0,
    )
