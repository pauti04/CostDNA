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


@dataclass
class TemperatureResult:
    """Result of post-hoc temperature scaling (Guo et al., 2017).

    Temperature T is fit on a held-out calibration split by minimizing NLL;
    ECE is then reported on a *separate* evaluation split (before and after
    scaling) so the number isn't fit on the data it's measured on.
    """
    temperature: float
    ece_before: float
    ece_after: float
    eval_n: int            # size of the evaluation split ECE is measured on
    calib_n: int           # size of the calibration split T was fit on


def _softmax(logits: np.ndarray) -> np.ndarray:
    z = logits - logits.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def apply_temperature(logits: np.ndarray, t: float) -> np.ndarray:
    """Return temperature-scaled softmax probabilities: softmax(logits / t)."""
    return _softmax(logits / t)


def _nll(logits: np.ndarray, labels: np.ndarray, t: float) -> float:
    """Mean negative log-likelihood of the temperature-scaled softmax."""
    probs = _softmax(logits / t)
    n = len(labels)
    p_true = probs[np.arange(n), labels]
    return float(-np.log(np.clip(p_true, 1e-12, 1.0)).mean())


def fit_temperature(logits: np.ndarray, labels: np.ndarray,
                    bounds: tuple[float, float] = (0.05, 10.0)) -> float:
    """Fit a single temperature scalar T (Guo et al., 2017).

    Minimizes NLL of softmax(logits / T) on the supplied (calibration) set.
    T > 1 softens overconfident logits; T < 1 sharpens underconfident ones;
    T = 1 leaves the model unchanged. The standard protocol fits T on a
    held-out validation/calibration split and reports ECE on a *separate*
    evaluation split — see `temperature_calibration` below.
    """
    from scipy.optimize import minimize_scalar
    if len(labels) == 0:
        return 1.0
    res = minimize_scalar(lambda t: _nll(logits, labels, t),
                          bounds=bounds, method="bounded")
    return float(res.x)


def temperature_calibration(
    logits: np.ndarray,
    y_true: np.ndarray,
    *,
    seed: int = 7,
    calib_frac: float = 0.5,
    n_bins: int = 10,
) -> TemperatureResult:
    """Full post-hoc temperature-scaling protocol on a single labeled set.

    Splits the labeled nodes into a calibration half (fit T) and an
    evaluation half (report ECE), stratified by class, with a fixed seed.
    Reports ECE before and after scaling, both measured on the held-out
    evaluation split — so T is never fit on the data its quality is judged
    on. This is the honest version: a low post-scaling ECE here is on a
    genuinely held-out split, not on the training nodes.
    """
    rng = np.random.default_rng(seed)
    idx = np.arange(len(y_true))

    # Stratified calib/eval split so every class appears on both sides.
    calib_idx, eval_idx = [], []
    for cls in np.unique(y_true):
        cls_idx = idx[y_true == cls]
        rng.shuffle(cls_idx)
        cut = max(1, int(len(cls_idx) * calib_frac))
        calib_idx.extend(cls_idx[:cut])
        eval_idx.extend(cls_idx[cut:] if len(cls_idx) > 1 else cls_idx[:cut])
    calib_idx = np.array(calib_idx)
    eval_idx = np.array(eval_idx)

    t = fit_temperature(logits[calib_idx], y_true[calib_idx])

    def _ece_on(indices: np.ndarray, temp: float) -> float:
        probs = _softmax(logits[indices] / temp)
        preds = probs.argmax(axis=1)
        confs = probs.max(axis=1)
        return calibration_curve(preds, confs, y_true[indices],
                                 n_bins=n_bins).ece

    return TemperatureResult(
        temperature=t,
        ece_before=_ece_on(eval_idx, 1.0),
        ece_after=_ece_on(eval_idx, t),
        eval_n=int(len(eval_idx)),
        calib_n=int(len(calib_idx)),
    )


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
