from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reflectogen import (
    GeneratorConfig,
    generate_image_array,
    image_distance,
    parse_filename,
    render_reflectogram,
    synthesize_signal,
)


SCRIPT = ROOT / "reflectogen.py"


def run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd or ROOT,
        check=True,
        text=True,
        capture_output=True,
    )


def test_parse_filename_valid() -> None:
    assert parse_filename("Rectangular_10.0_10.5_-20.png") == (
        "Rectangular",
        10.0,
        10.5,
        -20.0,
    )


def test_parse_filename_invalid() -> None:
    with pytest.raises(ValueError):
        parse_filename("bad_name.png")


def test_synthesize_signal_and_render_are_finite() -> None:
    cfg = GeneratorConfig()
    time_s, signal, z_m, area_m2 = synthesize_signal(cfg, "Round", 12.0, 12.5, 15)

    assert time_s.shape == (cfg.n_samples,)
    assert signal.shape == (cfg.n_samples,)
    assert z_m.ndim == 1
    assert area_m2.shape == z_m.shape
    assert np.isfinite(signal).all()
    assert np.max(np.abs(signal)) <= 1.000001

    img = render_reflectogram(cfg, signal)
    assert img.size == (cfg.render_width, cfg.render_height)


def test_generate_image_array_shape() -> None:
    cfg = GeneratorConfig(render_width=160, render_height=64)
    arr = generate_image_array(cfg, "Triangular", 10.0, 11.0, -30)
    assert arr.shape == (64, 160)
    assert 0.0 <= float(arr.min()) <= float(arr.max()) <= 1.0


def test_image_distance_identical_is_zero() -> None:
    cfg = GeneratorConfig(render_width=120, render_height=60)
    arr = generate_image_array(cfg, "Rectangular", 10.0, 10.5, -20)
    assert image_distance(arr, arr) == pytest.approx(0.0)


def test_cli_version() -> None:
    result = run_cli("--version")
    assert "ReflectoGen 1.0.0" in result.stdout


def test_cli_one_and_batch(tmp_path: Path) -> None:
    one_out = tmp_path / "one" / "Rectangular_10.0_10.5_-20.png"
    run_cli(
        "one",
        "--shape",
        "Rectangular",
        "--start",
        "10.0",
        "--end",
        "10.5",
        "--percent",
        "-20",
        "--out",
        str(one_out),
        "--save-signal-csv",
        "--save-profile-csv",
    )

    assert one_out.exists()
    assert one_out.with_suffix(".meta.json").exists()
    assert one_out.with_suffix(".signal.csv").exists()
    assert one_out.with_suffix(".profile.csv").exists()

    params = tmp_path / "params.csv"
    run_cli("template", "--out", str(params))
    assert params.exists()

    batch_dir = tmp_path / "batch"
    run_cli("batch", "--csv", str(params), "--out-dir", str(batch_dir))
    manifest = batch_dir / "manifest.json"
    assert manifest.exists()
    assert len(json.loads(manifest.read_text(encoding="utf-8"))) == 3


def test_cli_calibrate_smoke(tmp_path: Path) -> None:
    # Build a tiny self-generated archive. This is only a smoke test for the
    # calibration pipeline, not a validation of physical accuracy.
    archive = tmp_path / "demo_archive.zip"
    cfg = GeneratorConfig(render_width=80, render_height=40, n_samples=512, oversample_factor=4)
    cases = [
        ("Rectangular", 10.0, 10.5, -20),
        ("Round", 15.0, 15.5, 12),
    ]
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for shape, start, end, pct in cases:
            _, signal, _, _ = synthesize_signal(cfg, shape, start, end, pct)
            img = render_reflectogram(cfg, signal)
            img_path = tmp_path / f"{shape}_{start}_{end}_{pct}.png"
            img.save(img_path)
            zf.write(img_path, arcname=img_path.name)

    out_dir = tmp_path / "calibration"
    run_cli(
        "calibrate",
        "--input",
        str(archive),
        "--out",
        str(out_dir),
        "--max-images",
        "2",
        "--stages",
        "1",
        "--trials-per-stage",
        "1",
        "--seed",
        "7",
    )

    assert (out_dir / "best_config.json").exists()
    assert (out_dir / "fit_summary.json").exists()
    assert (out_dir / "search_history.csv").exists()
    assert (out_dir / "fit_records.csv").exists()
    assert (out_dir / "fit_preview.png").exists()
