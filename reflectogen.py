"""ReflectoGen: physics-inspired and calibration-enabled reflectogram synthesis.

This module provides a command-line and importable Python implementation for
physics-inspired synthetic reflectogram generation in pile integrity testing. It
supports single-case generation, batch generation from a parameter CSV, and
calibration of global generator parameters against existing reflectogram
archives.

The model is intentionally transparent rather than proprietary. It uses a
one-dimensional impedance-change formulation, source-pulse convolution, temporal
attenuation, and grayscale rendering to create reproducible synthetic
reflectograms suitable for benchmark construction and machine-learning workflows.

SoftwareX manuscript title:
    ReflectoGen: Physics-Inspired and Calibration-Enabled Reflectogram Synthesis
    for Pile Integrity Testing
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import random
import zipfile
from dataclasses import dataclass, asdict, fields
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np
from PIL import Image, ImageDraw


# -----------------------------------------------------------------------------
# Core generator
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class GeneratorConfig:
    """Configuration parameters for the ReflectoGen synthetic reflectogram generator.

    The fields describe both the simplified physical model and the rendering
    settings. The physical parameters define the pile geometry, wave speed,
    material density, source-pulse behavior, damping, toe-reflection strength,
    and numerical sampling. The rendering parameters control the final grayscale
    reflectogram image size and stroke appearance.
    """

    pile_length_m: float = 30.0
    pile_diameter_m: float = 0.50
    wave_speed_m_s: float = 3900.0
    density_kg_m3: float = 2450.0
    toe_reflection_coeff: float = 0.85
    damping_alpha: float = 45.0
    dz_m: float = 0.01
    oversample_factor: int = 8
    n_samples: int = 2048
    f0_hz: float = 2500.0
    t_margin_factor: float = 1.20
    source_amplitude: float = 1.0
    source_delay_s: float = 0.00025
    render_width: int = 300
    render_height: int = 100
    line_width: int = 2
    background: int = 255
    foreground: int = 0
    vertical_margin_px: int = 6


@dataclass(frozen=True)
class Record:
    """Container for one existing reflectogram used during calibration.

    Attributes
    ----------
    filename:
        Original image filename.
    shape:
        Defect-envelope family parsed from the filename.
    start_m:
        Defect start location in meters.
    end_m:
        Defect end location in meters.
    percent_change:
        Signed cross-sectional change percentage.
    image:
        Grayscale image array normalized to the [0, 1] range.
    """

    filename: str
    shape: str
    start_m: float
    end_m: float
    percent_change: float
    image: np.ndarray  # float32 in [0,1], black line on white background


def parse_filename(name: str) -> Tuple[str, float, float, float]:
    """Parse defect parameters from a reflectogram filename.

    Expected filenames follow the convention
    ``Shape_start_m_end_m_percent_change.png``. The extension is ignored.

    Parameters
    ----------
    name:
        Filename or path-like string to parse.

    Returns
    -------
    tuple
        ``(shape, start_m, end_m, percent_change)``.

    Raises
    ------
    ValueError
        If the filename does not contain exactly four underscore-separated
        components before the extension or if numeric fields cannot be parsed.
    """

    stem = Path(name).stem
    parts = stem.split("_")
    if len(parts) != 4:
        raise ValueError(f"Filename is not in expected format Shape_start_end_percent: {name}")
    shape, start_s, end_s, pct_s = parts
    return shape, float(start_s), float(end_s), float(pct_s)


def _shape_envelope(shape: str, z: np.ndarray, start_m: float, end_m: float) -> np.ndarray:
    """Build a normalized spatial defect envelope along the pile axis.

    The envelope is zero outside the defect interval and varies between 0 and 1
    inside the interval. Rectangular defects are constant, round defects are
    raised-cosine bumps, and triangular defects rise and fall linearly.

    Parameters
    ----------
    shape:
        One of ``Rectangular``, ``Round``, or ``Triangular``.
    z:
        Axial coordinate vector in meters.
    start_m:
        Defect start coordinate in meters.
    end_m:
        Defect end coordinate in meters.

    Returns
    -------
    numpy.ndarray
        Normalized defect envelope sampled at ``z``.

    Raises
    ------
    ValueError
        If the end coordinate is not greater than the start coordinate or if the
        requested shape is unsupported.
    """

    if end_m <= start_m:
        raise ValueError("end_m must be greater than start_m")
    env = np.zeros_like(z, dtype=np.float64)
    mask = (z >= start_m) & (z <= end_m)
    if not np.any(mask):
        return env
    xi = (z[mask] - start_m) / (end_m - start_m)
    s = shape.lower()
    if s == "rectangular":
        env[mask] = 1.0
    elif s == "round":
        env[mask] = 0.5 * (1.0 - np.cos(2.0 * np.pi * xi))
    elif s == "triangular":
        env[mask] = 1.0 - np.abs(2.0 * xi - 1.0)
    else:
        raise ValueError(f"Unsupported shape: {shape}")
    return env


def build_area_profile(
    cfg: GeneratorConfig,
    shape: str,
    start_m: float,
    end_m: float,
    percent_change: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Construct the axial cross-sectional area profile of the pile.

    A cylindrical pile is assumed as the reference geometry. The local defect
    envelope modifies the reference cross-sectional area according to the signed
    percentage change. A lower bound is applied to avoid nonphysical negative or
    near-zero section values.

    Parameters
    ----------
    cfg:
        Generator configuration.
    shape:
        Defect-envelope family.
    start_m:
        Defect start location in meters.
    end_m:
        Defect end location in meters.
    percent_change:
        Signed cross-sectional change percentage.

    Returns
    -------
    tuple of numpy.ndarray
        ``(z, area)`` where ``z`` is the axial coordinate vector and ``area`` is
        the corresponding cross-sectional area in square meters.
    """

    z = np.arange(0.0, cfg.pile_length_m + cfg.dz_m, cfg.dz_m, dtype=np.float64)
    r0 = cfg.pile_diameter_m / 2.0
    a0 = math.pi * r0 * r0
    env = _shape_envelope(shape, z, start_m, end_m)
    frac = percent_change / 100.0
    area = a0 * (1.0 + frac * env)
    area = np.clip(area, 0.05 * a0, None)
    return z, area


def compute_reflection_impulses(
    cfg: GeneratorConfig,
    z: np.ndarray,
    area: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute first-order reflection events from impedance changes.

    The local acoustic impedance is approximated as density times wave speed
    times cross-sectional area. Reflection coefficients are computed between
    adjacent axial samples. The function also adds a source event and a terminal
    toe reflection event.

    Parameters
    ----------
    cfg:
        Generator configuration.
    z:
        Axial coordinate vector in meters.
    area:
        Cross-sectional area profile sampled at ``z``.

    Returns
    -------
    tuple of numpy.ndarray
        Sorted event times in seconds and corresponding event amplitudes.
    """

    impedance = cfg.density_kg_m3 * cfg.wave_speed_m_s * area
    rc = (impedance[1:] - impedance[:-1]) / (impedance[1:] + impedance[:-1])
    z_mid = 0.5 * (z[1:] + z[:-1])
    keep = np.abs(rc) > 1e-6
    rc = rc[keep]
    z_mid = z_mid[keep]
    t_local = 2.0 * z_mid / cfg.wave_speed_m_s

    t_toe = np.array([2.0 * cfg.pile_length_m / cfg.wave_speed_m_s], dtype=np.float64)
    a_toe = np.array([cfg.toe_reflection_coeff], dtype=np.float64)
    t_src = np.array([cfg.source_delay_s], dtype=np.float64)
    a_src = np.array([cfg.source_amplitude], dtype=np.float64)

    times = np.concatenate([t_src, t_local, t_toe])
    amps = np.concatenate([a_src, rc, a_toe])
    order = np.argsort(times)
    return times[order], amps[order]


def ricker_wavelet(t: np.ndarray, f0_hz: float) -> np.ndarray:
    """Evaluate a Ricker wavelet at the supplied time offsets.

    Parameters
    ----------
    t:
        Time offsets in seconds, typically centered around zero.
    f0_hz:
        Central frequency of the Ricker wavelet in hertz.

    Returns
    -------
    numpy.ndarray
        Ricker wavelet samples evaluated at ``t``.
    """

    x = math.pi * f0_hz * t
    return (1.0 - 2.0 * x * x) * np.exp(-(x * x))


def synthesize_signal(
    cfg: GeneratorConfig,
    shape: str,
    start_m: float,
    end_m: float,
    percent_change: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Generate a normalized one-dimensional LSPIT-like response signal.

    The signal is built by computing impedance-change reflection impulses,
    convolving them with a Ricker source wavelet, applying exponential temporal
    attenuation, downsampling to the requested sample count, removing the early
    baseline, and normalizing by maximum absolute amplitude.

    Parameters
    ----------
    cfg:
        Generator configuration.
    shape:
        Defect-envelope family.
    start_m:
        Defect start location in meters.
    end_m:
        Defect end location in meters.
    percent_change:
        Signed cross-sectional change percentage.

    Returns
    -------
    tuple of numpy.ndarray
        ``(time_s, signal, z_m, area_m2)``. The signal is normalized and stored
        as ``float32``.
    """

    z, area = build_area_profile(cfg, shape, start_m, end_m, percent_change)
    event_times, event_amps = compute_reflection_impulses(cfg, z, area)
    t_end = cfg.t_margin_factor * (2.0 * cfg.pile_length_m / cfg.wave_speed_m_s)
    n_hi = cfg.n_samples * cfg.oversample_factor
    t = np.linspace(0.0, t_end, n_hi, dtype=np.float64)
    dt = t[1] - t[0]

    impulse = np.zeros_like(t)
    idx = np.clip(np.round(event_times / dt).astype(int), 0, n_hi - 1)
    np.add.at(impulse, idx, event_amps)

    wavelet_half = int(round(0.002 / dt))
    tau = np.arange(-wavelet_half, wavelet_half + 1, dtype=np.float64) * dt
    wavelet = ricker_wavelet(tau, cfg.f0_hz)
    signal_hi = np.convolve(impulse, wavelet, mode="same")
    signal_hi *= np.exp(-cfg.damping_alpha * t)

    signal = signal_hi.reshape(cfg.n_samples, cfg.oversample_factor).mean(axis=1)
    t_final = np.linspace(0.0, t_end, cfg.n_samples, dtype=np.float64)
    signal = signal - np.mean(signal[: max(8, cfg.n_samples // 50)])
    mx = np.max(np.abs(signal))
    if mx > 0:
        signal = signal / mx
    return t_final, signal.astype(np.float32), z.astype(np.float32), area.astype(np.float32)


def render_reflectogram(cfg: GeneratorConfig, signal: np.ndarray) -> Image.Image:
    """Render a one-dimensional signal as a grayscale reflectogram image.

    Parameters
    ----------
    cfg:
        Generator configuration controlling image size and line appearance.
    signal:
        Normalized one-dimensional response signal.

    Returns
    -------
    PIL.Image.Image
        Grayscale image containing the rendered reflectogram trace.
    """

    w, h = cfg.render_width, cfg.render_height
    img = Image.new("L", (w, h), color=cfg.background)
    draw = ImageDraw.Draw(img)
    margin = cfg.vertical_margin_px
    center_y = h / 2.0
    amp_scale = (h / 2.0 - margin)

    x_src = np.linspace(0, len(signal) - 1, len(signal))
    x_tgt = np.linspace(0, len(signal) - 1, w)
    y = np.interp(x_tgt, x_src, signal)
    pts = [(float(i), float(center_y - val * amp_scale)) for i, val in enumerate(y)]
    draw.line(pts, fill=cfg.foreground, width=cfg.line_width)
    return img


def generate_image_array(
    cfg: GeneratorConfig,
    shape: str,
    start_m: float,
    end_m: float,
    percent_change: float,
) -> np.ndarray:
    """Generate a reflectogram image and return it as a normalized array.

    Parameters
    ----------
    cfg:
        Generator configuration.
    shape:
        Defect-envelope family.
    start_m:
        Defect start location in meters.
    end_m:
        Defect end location in meters.
    percent_change:
        Signed cross-sectional change percentage.

    Returns
    -------
    numpy.ndarray
        Grayscale image array normalized to the [0, 1] range.
    """

    _, signal, _, _ = synthesize_signal(cfg, shape, start_m, end_m, percent_change)
    img = render_reflectogram(cfg, signal)
    return np.asarray(img, dtype=np.float32) / 255.0


# -----------------------------------------------------------------------------
# IO helpers
# -----------------------------------------------------------------------------
def load_records(source: str, max_images: Optional[int] = None, seed: int = 42) -> List[Record]:
    """Load existing reflectogram images for calibration.

    The source may be a directory or a ZIP archive. Filenames are parsed to
    extract defect metadata using :func:`parse_filename`. Invalid filenames are
    skipped. Images are loaded as grayscale arrays normalized to [0, 1].

    Parameters
    ----------
    source:
        Directory path or ZIP file path containing reflectogram images.
    max_images:
        Optional maximum number of records to retain. If supplied, a random
        subset is selected for faster calibration.
    seed:
        Random seed used when subsampling records.

    Returns
    -------
    list of Record
        Calibration records containing parsed metadata and image arrays.
    """

    path = Path(source)
    records: List[Record] = []
    if path.is_dir():
        names = sorted([p for p in path.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"}])
        for p in names:
            try:
                shape, start, end, pct = parse_filename(p.name)
            except Exception:
                continue
            arr = np.asarray(Image.open(p).convert("L"), dtype=np.float32) / 255.0
            records.append(Record(p.name, shape, start, end, pct, arr))
    else:
        with zipfile.ZipFile(path) as zf:
            names = [n for n in sorted(zf.namelist()) if n.lower().endswith((".png", ".jpg", ".jpeg"))]
            for name in names:
                base = Path(name).name
                try:
                    shape, start, end, pct = parse_filename(base)
                except Exception:
                    continue
                with zf.open(name) as f:
                    img = Image.open(io.BytesIO(f.read())).convert("L")
                    arr = np.asarray(img, dtype=np.float32) / 255.0
                records.append(Record(base, shape, start, end, pct, arr))

    if max_images is not None and len(records) > max_images:
        rng = random.Random(seed)
        records = rng.sample(records, max_images)
        records = sorted(records, key=lambda r: r.filename)
    return records


def make_name(shape: str, start_m: float, end_m: float, percent_change: float) -> str:
    """Create a reflectogram filename from defect parameters.

    Parameters
    ----------
    shape:
        Defect-envelope family.
    start_m:
        Defect start location in meters.
    end_m:
        Defect end location in meters.
    percent_change:
        Signed cross-sectional change percentage.

    Returns
    -------
    str
        Filename in the form ``Shape_start_end_percent.png``.
    """

    pct = int(percent_change) if float(percent_change).is_integer() else percent_change
    return f"{shape}_{start_m}_{end_m}_{pct}.png"


def json_save(path: Path, obj: object) -> None:
    """Write an object to a JSON file with indentation.

    Parameters
    ----------
    path:
        Output JSON path.
    obj:
        JSON-serializable object to write.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def load_config_json(path: Optional[str]) -> GeneratorConfig:
    """Load a generator configuration from JSON.

    Unknown keys are ignored so that configuration files can contain additional
    metadata without breaking the generator.

    Parameters
    ----------
    path:
        Path to a JSON configuration file. If ``None`` or empty, the default
        configuration is returned.

    Returns
    -------
    GeneratorConfig
        Loaded or default generator configuration.
    """

    if not path:
        return GeneratorConfig()
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    valid = {f.name for f in fields(GeneratorConfig)}
    filtered = {k: v for k, v in data.items() if k in valid}
    return GeneratorConfig(**filtered)


# -----------------------------------------------------------------------------
# Calibration helpers
# -----------------------------------------------------------------------------
def smooth_binary(arr: np.ndarray) -> np.ndarray:
    """Convert a grayscale image into a normalized dark-pixel weight map.

    Parameters
    ----------
    arr:
        Grayscale image array normalized to [0, 1].

    Returns
    -------
    numpy.ndarray
        Inverted and normalized image where dark pixels receive large weights.
    """

    inv = 1.0 - arr
    return inv / (inv.max() + 1e-8)


def trace_from_image(arr: np.ndarray) -> np.ndarray:
    """Extract a one-dimensional trace from a grayscale reflectogram image.

    The trace is computed as the vertical center of mass of dark pixels in each
    image column and normalized by image height.

    Parameters
    ----------
    arr:
        Grayscale image array normalized to [0, 1].

    Returns
    -------
    numpy.ndarray
        Normalized trace location for each image column.
    """

    inv = smooth_binary(arr)
    h, w = inv.shape
    y = np.arange(h, dtype=np.float32)[:, None]
    weights = inv + 1e-6
    trace = (y * weights).sum(axis=0) / weights.sum(axis=0)
    return trace / max(h - 1, 1)


def image_distance(target: np.ndarray, pred: np.ndarray) -> float:
    """Compute a combined image and trace similarity loss.

    The calibration loss combines pixel-level mean squared error with a trace
    centerline mean squared error. The trace term is weighted more strongly to
    emphasize waveform shape and vertical trajectory alignment.

    Parameters
    ----------
    target:
        Reference reflectogram image normalized to [0, 1].
    pred:
        Generated reflectogram image normalized to [0, 1].

    Returns
    -------
    float
        Weighted distance value; lower values indicate closer agreement.
    """

    if target.shape != pred.shape:
        target = np.asarray(Image.fromarray((target * 255).astype(np.uint8)).resize(pred.shape[::-1], Image.BILINEAR), dtype=np.float32) / 255.0
    pixel_mse = float(np.mean((target - pred) ** 2))
    trace_mse = float(np.mean((trace_from_image(target) - trace_from_image(pred)) ** 2))
    return 0.35 * pixel_mse + 0.65 * trace_mse


def evaluate_config(cfg: GeneratorConfig, records: List[Record]) -> Tuple[float, List[float]]:
    """Evaluate one generator configuration against calibration records.

    Parameters
    ----------
    cfg:
        Candidate generator configuration.
    records:
        Calibration records with target images and parsed metadata.

    Returns
    -------
    tuple
        Mean calibration loss and per-record loss values.
    """

    losses = []
    for rec in records:
        pred = generate_image_array(cfg, rec.shape, rec.start_m, rec.end_m, rec.percent_change)
        losses.append(image_distance(rec.image, pred))
    return float(np.mean(losses)), losses


PARAM_RANGES = {
    "wave_speed_m_s": (3200.0, 4700.0),
    "toe_reflection_coeff": (0.35, 1.25),
    "damping_alpha": (8.0, 95.0),
    "f0_hz": (1000.0, 4200.0),
    "source_delay_s": (0.00005, 0.00060),
    "t_margin_factor": (1.00, 1.45),
    "line_width": (1, 3),
    "vertical_margin_px": (3, 12),
}


def sample_random_config(
    rng: random.Random,
    base: Optional[GeneratorConfig] = None,
    sigma_scale: float = 1.0,
) -> GeneratorConfig:
    """Sample a random generator configuration for calibration search.

    When no base configuration is supplied, parameters are sampled uniformly from
    predefined ranges. When a base configuration is supplied, values are sampled
    from clipped Gaussian perturbations around the base to support local
    refinement.

    Parameters
    ----------
    rng:
        Random number generator.
    base:
        Optional base configuration for local perturbation.
    sigma_scale:
        Scale factor controlling perturbation width. Values below 1.0 favor
        local search around ``base``.

    Returns
    -------
    GeneratorConfig
        Randomly sampled candidate configuration.
    """

    base = base or GeneratorConfig()
    params = asdict(base)
    for key, bounds in PARAM_RANGES.items():
        lo, hi = bounds
        cur = params[key]
        if isinstance(cur, int):
            if sigma_scale < 1.0:
                span = max(1.0, (hi - lo) * 0.2 * sigma_scale)
                val = int(round(min(hi, max(lo, rng.gauss(cur, span)))))
            else:
                val = rng.randint(int(lo), int(hi))
        else:
            if sigma_scale < 1.0:
                span = (hi - lo) * 0.18 * sigma_scale
                val = min(hi, max(lo, rng.gauss(float(cur), span)))
            else:
                val = rng.uniform(lo, hi)
        params[key] = val
    return GeneratorConfig(**params)


def make_preview(records: List[Record], cfg: GeneratorConfig, out_path: Path, n_show: int = 10) -> None:
    """Create a side-by-side preview of target and generated reflectograms.

    The preview places each target image in the left column and the corresponding
    generated image in the right column. It is intended as a quick visual quality
    check after calibration.

    Parameters
    ----------
    records:
        Calibration records to display.
    cfg:
        Generator configuration used for the generated column.
    out_path:
        Output image path for the preview.
    n_show:
        Maximum number of record pairs to display.
    """

    if not records:
        return
    sample = records[: min(n_show, len(records))]
    cell_w, cell_h = cfg.render_width, cfg.render_height
    canvas = Image.new("L", (cell_w * 2, cell_h * len(sample)), 255)
    for i, rec in enumerate(sample):
        target = Image.fromarray((rec.image * 255).astype(np.uint8))
        pred = Image.fromarray((generate_image_array(cfg, rec.shape, rec.start_m, rec.end_m, rec.percent_change) * 255).astype(np.uint8))
        if target.size != (cell_w, cell_h):
            target = target.resize((cell_w, cell_h), Image.BILINEAR)
        canvas.paste(target, (0, i * cell_h))
        canvas.paste(pred, (cell_w, i * cell_h))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)


def cmd_calibrate(args: argparse.Namespace) -> None:
    """Run command-line calibration against an existing reflectogram archive.

    The function loads target records from a directory or ZIP file, evaluates the
    default configuration, performs staged random search with local refinement,
    saves the best configuration, writes search history and per-record losses,
    and creates a visual fit preview.

    Parameters
    ----------
    args:
        Parsed command-line arguments for the ``calibrate`` subcommand.
    """

    records = load_records(args.input, max_images=args.max_images, seed=args.seed)
    if not records:
        raise RuntimeError("No reflectogram images could be loaded from the given input.")

    rng = random.Random(args.seed)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    default_cfg = GeneratorConfig(render_width=records[0].image.shape[1], render_height=records[0].image.shape[0])
    best_cfg = default_cfg
    best_loss, _ = evaluate_config(best_cfg, records)
    history = [{"stage": "default", "loss": best_loss, **asdict(best_cfg)}]
    print(f"[INFO] Default loss: {best_loss:.6f}")

    for stage in range(args.stages):
        sigma = 1.0 if stage == 0 else max(0.15, 0.55 / stage)
        for trial in range(args.trials_per_stage):
            cand = sample_random_config(rng, None if stage == 0 else best_cfg, sigma_scale=sigma)
            cand = GeneratorConfig(**{**asdict(cand), "render_width": default_cfg.render_width, "render_height": default_cfg.render_height})
            loss, _ = evaluate_config(cand, records)
            history.append({"stage": f"stage_{stage+1}", "trial": trial + 1, "loss": loss, **asdict(cand)})
            if loss < best_loss:
                best_loss = loss
                best_cfg = cand
                print(f"[INFO] New best at stage {stage+1} trial {trial+1}: {best_loss:.6f}")

    final_loss, losses = evaluate_config(best_cfg, records)
    summary = {
        "n_records": len(records),
        "mean_loss": final_loss,
        "median_loss": float(np.median(losses)),
        "min_loss": float(np.min(losses)),
        "max_loss": float(np.max(losses)),
        "best_config": asdict(best_cfg),
    }

    json_save(out_dir / "best_config.json", asdict(best_cfg))
    json_save(out_dir / "fit_summary.json", summary)
    with (out_dir / "search_history.csv").open("w", newline="", encoding="utf-8") as f:
        fieldnames = sorted({k for row in history for k in row.keys()})
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(history)
    with (out_dir / "fit_records.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "shape", "start_m", "end_m", "percent_change", "loss"])
        for rec, loss in zip(records, losses):
            writer.writerow([rec.filename, rec.shape, rec.start_m, rec.end_m, rec.percent_change, f"{loss:.8f}"])
    make_preview(records, best_cfg, out_dir / "fit_preview.png", n_show=min(12, len(records)))
    print(f"[DONE] Best mean loss = {final_loss:.6f}")
    print(f"[DONE] Results written to: {out_dir}")


# -----------------------------------------------------------------------------
# Generate helpers
# -----------------------------------------------------------------------------
def save_signal_csv(path: Path, t: np.ndarray, signal: np.ndarray) -> None:
    """Save a generated time-domain signal to CSV.

    Parameters
    ----------
    path:
        Output CSV path.
    t:
        Time vector in seconds.
    signal:
        Normalized reflectogram signal amplitude.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", "amplitude"])
        for ti, yi in zip(t, signal):
            writer.writerow([f"{ti:.9f}", f"{yi:.9f}"])


def save_profile_csv(path: Path, z: np.ndarray, area: np.ndarray) -> None:
    """Save an axial cross-sectional area profile to CSV.

    Parameters
    ----------
    path:
        Output CSV path.
    z:
        Axial coordinate vector in meters.
    area:
        Cross-sectional area profile in square meters.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["z_m", "area_m2"])
        for zi, ai in zip(z, area):
            writer.writerow([f"{zi:.6f}", f"{ai:.9f}"])


def cmd_one(args: argparse.Namespace) -> None:
    """Generate one reflectogram image from command-line arguments.

    The function optionally loads a calibrated configuration, overrides image
    size if requested, generates the signal and image, and saves optional signal
    and area-profile CSV files.

    Parameters
    ----------
    args:
        Parsed command-line arguments for the ``one`` subcommand.
    """

    cfg = load_config_json(args.config_json)
    cfg = GeneratorConfig(**{**asdict(cfg), "render_width": args.width or cfg.render_width, "render_height": args.height or cfg.render_height})
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    t, signal, z, area = synthesize_signal(cfg, args.shape, args.start, args.end, args.percent)
    render_reflectogram(cfg, signal).save(out_path)
    if args.save_signal_csv:
        save_signal_csv(out_path.with_suffix(".signal.csv"), t, signal)
    if args.save_profile_csv:
        save_profile_csv(out_path.with_suffix(".profile.csv"), z, area)
    json_save(out_path.with_suffix(".meta.json"), {"shape": args.shape, "start_m": args.start, "end_m": args.end, "percent_change": args.percent, **asdict(cfg)})


def cmd_batch(args: argparse.Namespace) -> None:
    """Generate a batch of reflectograms from a parameter CSV file.

    The input CSV must contain ``shape``, ``start_m``, ``end_m``, and
    ``percent_change`` columns. For each row, a reflectogram image is generated
    and saved using the standard parameter-derived filename. A JSON manifest is
    written to the output directory.

    Parameters
    ----------
    args:
        Parsed command-line arguments for the ``batch`` subcommand.
    """

    cfg = load_config_json(args.config_json)
    cfg = GeneratorConfig(**{**asdict(cfg), "render_width": args.width or cfg.render_width, "render_height": args.height or cfg.render_height})
    csv_path = Path(args.csv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"shape", "start_m", "end_m", "percent_change"}
        if not required.issubset(reader.fieldnames or set()):
            raise ValueError(f"CSV must contain columns: {sorted(required)}")
        rows = list(reader)

    manifest = []
    for row in rows:
        shape = str(row["shape"])
        start = float(row["start_m"])
        end = float(row["end_m"])
        pct = float(row["percent_change"])
        name = make_name(shape, start, end, pct)
        out_path = out_dir / name
        t, signal, z, area = synthesize_signal(cfg, shape, start, end, pct)
        render_reflectogram(cfg, signal).save(out_path)
        if args.save_signal_csv:
            save_signal_csv(out_path.with_suffix(".signal.csv"), t, signal)
        if args.save_profile_csv:
            save_profile_csv(out_path.with_suffix(".profile.csv"), z, area)
        manifest.append({"filename": name, "shape": shape, "start_m": start, "end_m": end, "percent_change": pct})

    json_save(out_dir / "manifest.json", manifest)


def cmd_template(args: argparse.Namespace) -> None:
    """Write a minimal parameter CSV template for batch generation.

    Parameters
    ----------
    args:
        Parsed command-line arguments for the ``template`` subcommand.
    """

    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["shape", "start_m", "end_m", "percent_change"])
        writer.writerow(["Rectangular", 10.0, 10.5, -20])
        writer.writerow(["Round", 15.0, 15.5, 12])
        writer.writerow(["Rectangular", 20.0, 21.0, -35])


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
def add_output_args(p: argparse.ArgumentParser) -> None:
    """Add common output-related arguments to a subparser.

    Parameters
    ----------
    p:
        Subparser to which common rendering and export options are added.
    """

    p.add_argument("--width", type=int, default=None)
    p.add_argument("--height", type=int, default=None)
    p.add_argument("--save-signal-csv", action="store_true")
    p.add_argument("--save-profile-csv", action="store_true")
    p.add_argument("--config-json", type=str, default=None, help="Optional best_config.json produced by calibrate.")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for ReflectoGen.

    Returns
    -------
    argparse.ArgumentParser
        Parser with ``calibrate``, ``one``, ``batch``, and ``template``
        subcommands.
    """

    p = argparse.ArgumentParser(description="ReflectoGen: physics-inspired and calibration-enabled reflectogram synthesis for pile integrity testing.")
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("calibrate", help="Fit global generator parameters to a zip/folder of existing reflectograms.")
    pc.add_argument("--input", type=str, required=True, help="Zip file or directory containing reflectograms named Shape_start_end_percent.png")
    pc.add_argument("--out", type=str, required=True)
    pc.add_argument("--max-images", type=int, default=250, help="Use a random subset for faster calibration.")
    pc.add_argument("--stages", type=int, default=3)
    pc.add_argument("--trials-per-stage", type=int, default=80)
    pc.add_argument("--seed", type=int, default=42)
    pc.set_defaults(func=cmd_calibrate)

    po = sub.add_parser("one", help="Generate one reflectogram.")
    po.add_argument("--shape", required=True, choices=["Rectangular", "Round", "Triangular"])
    po.add_argument("--start", type=float, required=True)
    po.add_argument("--end", type=float, required=True)
    po.add_argument("--percent", type=float, required=True)
    po.add_argument("--out", type=str, required=True)
    add_output_args(po)
    po.set_defaults(func=cmd_one)

    pb = sub.add_parser("batch", help="Generate many reflectograms from a CSV.")
    pb.add_argument("--csv", type=str, required=True)
    pb.add_argument("--out-dir", type=str, required=True)
    add_output_args(pb)
    pb.set_defaults(func=cmd_batch)

    pt = sub.add_parser("template", help="Write a CSV template for batch generation.")
    pt.add_argument("--out", type=str, required=True)
    pt.set_defaults(func=cmd_template)

    return p


def main() -> None:
    """Parse command-line arguments and dispatch the selected subcommand."""

    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
