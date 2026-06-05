"""Tests for post-hoc temperature scaling (Guo et al., 2017).

The synthetic env is already well-calibrated because accuracy is high, so to
prove the temperature fit actually *works* we construct deliberately
overconfident logits (95% confidence, 60% accuracy) and check that:
  1. fit_temperature returns T > 1 (softening the overconfidence)
  2. ECE drops materially after scaling
"""

from __future__ import annotations

import numpy as np

from costdna.calibrate import (apply_temperature, calibration_curve,
                               fit_temperature, temperature_calibration)


def _overconfident_logits(n=600, n_classes=3, accuracy=0.60, seed=0):
    """Build logits that are ~95% confident but only `accuracy` correct."""
    rng = np.random.default_rng(seed)
    logits = np.zeros((n, n_classes), dtype=np.float64)
    y_true = rng.integers(0, n_classes, size=n)
    for i in range(n):
        # The model "predicts" some class with a big margin (overconfident).
        if rng.random() < accuracy:
            pred = y_true[i]            # correct prediction
        else:
            # wrong prediction: pick a different class
            pred = (y_true[i] + 1 + rng.integers(0, n_classes - 1)) % n_classes
        logits[i, pred] = 4.0           # large logit → ~0.95+ softmax confidence
    return logits, y_true


def test_fit_temperature_softens_overconfidence():
    logits, y = _overconfident_logits(accuracy=0.60, seed=1)
    t = fit_temperature(logits, y)
    # Overconfident model → T should be > 1 to soften.
    assert t > 1.0, f"expected T>1 to soften overconfidence, got {t:.3f}"


def test_temperature_scaling_reduces_ece():
    logits, y = _overconfident_logits(accuracy=0.60, seed=2)

    raw_probs = apply_temperature(logits, 1.0)
    raw = calibration_curve(raw_probs.argmax(1), raw_probs.max(1), y)

    t = fit_temperature(logits, y)
    cal_probs = apply_temperature(logits, t)
    cal = calibration_curve(cal_probs.argmax(1), cal_probs.max(1), y)

    # Raw model is wildly overconfident (~0.95 conf, ~0.60 acc → ECE ~0.35).
    assert raw.ece > 0.20, f"setup invariant: raw ECE should be high, got {raw.ece:.3f}"
    # Temperature scaling should cut it substantially.
    assert cal.ece < raw.ece * 0.6, (
        f"temperature scaling should materially reduce ECE: "
        f"{raw.ece:.3f} → {cal.ece:.3f}"
    )


def test_temperature_calibration_protocol_holds_out_eval():
    """The full protocol fits T on a calibration split and reports ECE on a
    separate eval split. Both splits should be non-empty and the result
    should expose T + before/after ECE."""
    logits, y = _overconfident_logits(n=600, accuracy=0.6, seed=3)
    res = temperature_calibration(logits, y, seed=3)
    assert res.calib_n > 0 and res.eval_n > 0
    assert res.temperature > 1.0
    # On held-out eval, scaling should not make calibration worse by much
    # (it's fit to improve NLL on a disjoint split).
    assert res.ece_after <= res.ece_before + 0.05


def test_fit_temperature_sharpens_underconfidence():
    """Underconfident logits (low margin → ~0.35 confidence but ~50% accuracy)
    should yield T < 1 — temperature scaling sharpens as well as softens."""
    rng = np.random.default_rng(4)
    n, n_classes = 600, 3
    logits = np.zeros((n, n_classes))
    y = rng.integers(0, n_classes, size=n)
    for i in range(n):
        pred = y[i] if rng.random() < 0.5 else (y[i] + 1) % n_classes
        logits[i, pred] = 0.1           # tiny margin → underconfident
    t = fit_temperature(logits, y)
    assert t < 1.0, f"underconfident input should yield T<1 (sharpen), got {t:.3f}"
