#!/usr/bin/env python3
"""Run lightweight sanity checks for ReflectoGen response behavior.

The checks are intentionally simple. They are not field validation. They quantify
whether generated signals respond monotonically or consistently to controlled
changes in location, severity, sign, and support length.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reflectogen import GeneratorConfig, synthesize_signal


def signal_summary(
    cfg: GeneratorConfig,
    shape: str,
    start_m: float,
    end_m: float,
    percent_change: float,
) -> dict[str, float | str]:
    """Return simple response descriptors for one generated case."""

    time_s, signal, _, _ = synthesize_signal(cfg, shape, start_m, end_m, percent_change)
    base_time, baseline, _, _ = synthesize_signal(cfg, shape, start_m, end_m, 0.0)
    if len(base_time) != len(time_s):
        raise RuntimeError("Baseline and target signals have different lengths.")

    diff = signal - baseline
    skip = max(1, len(signal) // 20)  # avoid the immediate source pulse region
    idx = int(skip + np.argmax(np.abs(diff[skip:])))
    perturbation_energy = float(np.sqrt(np.mean(diff**2)))
    late_energy = float(np.sqrt(np.mean(diff[skip:] ** 2)))

    return {
        "shape": shape,
        "start_m": start_m,
        "end_m": end_m,
        "length_m": end_m - start_m,
        "percent_change": percent_change,
        "dominant_difference_time_s": float(time_s[idx]),
        "dominant_difference_index": idx,
        "perturbation_rmse": perturbation_energy,
        "late_perturbation_rmse": late_energy,
    }


def build_cases() -> list[tuple[str, str, float, float, float]]:
    """Create controlled sanity-check cases."""

    cases: list[tuple[str, str, float, float, float]] = []

    # Location shift: dominant defect response should move later in time.
    for start in [5.0, 10.0, 15.0, 20.0]:
        cases.append(("location_shift", "Rectangular", start, start + 0.5, -25.0))

    # Severity: perturbation energy should generally increase with magnitude.
    for pct in [-10.0, -25.0, -50.0, 10.0, 25.0, 50.0]:
        cases.append(("severity", "Rectangular", 10.0, 10.5, pct))

    # Sign: negative and positive section changes should produce different polarity/trajectory behavior.
    for pct in [-30.0, 30.0]:
        cases.append(("sign", "Round", 12.0, 12.5, pct))

    # Support length: longer intervals should change response spread/energy.
    for length in [0.125, 0.25, 0.5, 1.0]:
        cases.append(("support_length", "Round", 10.0, 10.0 + length, -25.0))

    return cases


def main() -> None:
    parser = argparse.ArgumentParser(description="Run lightweight ReflectoGen sanity checks.")
    parser.add_argument("--out", default="outputs/sanity_checks.csv", help="Output CSV path.")
    args = parser.parse_args()

    cfg = GeneratorConfig()
    rows = []
    for test_name, shape, start, end, pct in build_cases():
        row = signal_summary(cfg, shape, start, end, pct)
        row["test"] = test_name
        rows.append(row)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "test",
        "shape",
        "start_m",
        "end_m",
        "length_m",
        "percent_change",
        "dominant_difference_time_s",
        "dominant_difference_index",
        "perturbation_rmse",
        "late_perturbation_rmse",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[DONE] Sanity-check table written to: {out_path}")


if __name__ == "__main__":
    main()
