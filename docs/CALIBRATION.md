# Calibration guide

ReflectoGen calibration fits selected global generator parameters to an existing reflectogram archive. It is intended for reproducible reconstruction of synthetic-style archives when the original generating software is unavailable.

## Input archive requirements

Calibration accepts either a directory or ZIP file containing PNG/JPG reflectogram images.

Each filename must encode the defect metadata:

```text
Shape_start_m_end_m_percent_change.png
```

Examples:

```text
Rectangular_10.0_10.5_-20.png
Round_15.0_15.5_12.png
Triangular_20.0_21.0_-35.png
```

Files that do not match the convention are skipped.

## Example command

```bash
python reflectogen.py calibrate \
  --input legacy_reflectograms.zip \
  --out outputs/calibration_run \
  --max-images 250 \
  --stages 3 \
  --trials-per-stage 80 \
  --seed 42
```

## Search parameters

The staged random search varies:

| Parameter | Range |
|---|---:|
| `wave_speed_m_s` | `3200.0` – `4700.0` |
| `toe_reflection_coeff` | `0.35` – `1.25` |
| `damping_alpha` | `8.0` – `95.0` |
| `f0_hz` | `1000.0` – `4200.0` |
| `source_delay_s` | `0.00005` – `0.00060` |
| `t_margin_factor` | `1.00` – `1.45` |
| `line_width` | `1` – `3` |
| `vertical_margin_px` | `3` – `12` |

## Loss function

The calibration loss is:

```text
loss = 0.35 × pixel_mse + 0.65 × trace_mse
```

The trace term is weighted more strongly to emphasize waveform trajectory agreement.

## Outputs

| Output | Description |
|---|---|
| `best_config.json` | Best calibrated generator configuration |
| `fit_summary.json` | Number of records and loss statistics |
| `search_history.csv` | Full parameter-search history |
| `fit_records.csv` | Per-record losses |
| `fit_preview.png` | Side-by-side target/generated preview |

## Important limitation

Calibration improves similarity to the selected archive under a simplified one-dimensional model. It does not prove physical equivalence to a proprietary generator, field measurement system, or high-fidelity numerical solver.
