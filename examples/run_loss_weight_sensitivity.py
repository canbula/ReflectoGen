#!/usr/bin/env python3
"""Run a lightweight calibration-loss weighting sensitivity example.

This script creates a small ReflectoGen demo archive and evaluates several
pixel/trace loss-weight combinations using a compact calibration budget. It is
intended for documentation and reviewer-response reproducibility, not for
large-scale calibration.
"""

from __future__ import annotations

import argparse
import csv
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reflectogen import GeneratorConfig, cmd_calibrate, make_name, render_reflectogram, synthesize_signal  # noqa: E402


def run_one(
    archive: Path,
    base_out: Path,
    pixel_weight: float,
    trace_weight: float,
    stages: int,
    trials_per_stage: int,
    seed: int,
) -> dict[str, str | float]:
    """Run one compact calibration experiment and return summary values."""

    label = f"w{pixel_weight:.2f}_{trace_weight:.2f}".replace(".", "")
    out_dir = base_out / label
    args = SimpleNamespace(
        input=str(archive),
        out=str(out_dir),
        max_images=6,
        stages=stages,
        trials_per_stage=trials_per_stage,
        seed=seed,
        metadata_csv=None,
        pixel_weight=pixel_weight,
        trace_weight=trace_weight,
    )
    cmd_calibrate(args)
    import json

    summary = json.loads((out_dir / "fit_summary.json").read_text(encoding="utf-8"))
    return {
        "pixel_weight": pixel_weight,
        "trace_weight": trace_weight,
        "mean_loss": float(summary["mean_loss"]),
        "median_loss": float(summary["median_loss"]),
        "out_dir": str(out_dir),
    }


def main() -> None:
    """Run the example and write a sensitivity CSV table."""

    parser = argparse.ArgumentParser(description="Run ReflectoGen loss-weight sensitivity example.")
    parser.add_argument("--out", default="outputs/loss_weight_sensitivity.csv", help="Output CSV path.")
    parser.add_argument("--stages", type=int, default=1)
    parser.add_argument("--trials-per-stage", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    work_dir = out_path.parent / "loss_weight_sensitivity_runs"
    work_dir.mkdir(parents=True, exist_ok=True)
    archive = out_path.parent / "demo_legacy_reflectograms_shifted.zip"

    # Build a compact target archive with a deliberately shifted configuration so
    # that the default generator is not a perfect match.
    import tempfile
    import zipfile

    target_cfg = GeneratorConfig(
        wave_speed_m_s=3600.0,
        damping_alpha=28.0,
        f0_hz=1900.0,
        toe_reflection_coeff=0.70,
    )
    cases = [
        ("Rectangular", 10.0, 10.5, -20),
        ("Round", 10.0, 10.5, -20),
        ("Triangular", 10.0, 10.5, -20),
        ("Rectangular", 15.0, 16.0, 25),
        ("Round", 15.0, 16.0, 25),
        ("Triangular", 15.0, 16.0, 25),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for shape, start, end, pct in cases:
            _, signal, _, _ = synthesize_signal(target_cfg, shape, start, end, pct)
            img_path = tmp_dir / make_name(shape, start, end, pct)
            render_reflectogram(target_cfg, signal).save(img_path)
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for img_path in sorted(tmp_dir.glob("*.png")):
                zf.write(img_path, arcname=img_path.name)

    weights = [(0.50, 0.50), (0.35, 0.65), (0.25, 0.75), (0.10, 0.90)]
    rows = [run_one(archive, work_dir, wp, wt, args.stages, args.trials_per_stage, args.seed) for wp, wt in weights]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["pixel_weight", "trace_weight", "mean_loss", "median_loss", "out_dir"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"[DONE] Loss-weight sensitivity table written to: {out_path}")


if __name__ == "__main__":
    main()
