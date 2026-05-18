# Calibration guide

ReflectoGen calibration fits selected global generator parameters to an existing reflectogram archive. It is intended for reproducible reconstruction of synthetic-style archives when the original generating software is unavailable.

## Input archive requirements

Calibration accepts either a directory or ZIP file containing PNG/JPG reflectogram images. Metadata can be supplied in two ways.

### Option A: filename-derived metadata

Each filename can encode the defect metadata:

```text
Shape_start_m_end_m_percent_change.png
```

Examples:

```text
Rectangular_10.0_10.5_-20.png
Round_15.0_15.5_12.png
Triangular_20.0_21.0_-35.png
```

Files that do not match the convention are skipped unless a metadata CSV is provided.

### Option B: metadata CSV

If filenames are inconsistent, supply a CSV containing either `filename` or `relative_path` together with `shape`, `start_m`, `end_m`, and `percent_change`.

```csv
filename,shape,start_m,end_m,percent_change
case_001.png,Rectangular,10.0,10.5,-20
case_002.png,Round,15.0,15.5,12
```

## Reproducible demo command

Create a small demo archive first, then run calibration:

```bash
python examples/make_demo_archive.py --out outputs/demo_legacy_reflectograms.zip

python reflectogen.py calibrate \
  --input outputs/demo_legacy_reflectograms.zip \
  --out outputs/calibration_run \
  --max-images 6 \
  --stages 2 \
  --trials-per-stage 20 \
  --seed 42
```

For a user-supplied archive with external metadata:

```bash
python reflectogen.py calibrate \
  --input legacy_archive.zip \
  --metadata-csv legacy_metadata.csv \
  --out outputs/calibration_with_metadata
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
loss = (pixel_weight × pixel_mse + trace_weight × trace_mse) / (pixel_weight + trace_weight)
```

Defaults are `pixel_weight = 0.35` and `trace_weight = 0.65`. The trace term is weighted more strongly to emphasize waveform trajectory agreement. These weights can be changed with `--pixel-weight` and `--trace-weight`.

## Outputs

| Output | Description |
|---|---|
| `best_config.json` | Best calibrated generator configuration |
| `fit_summary.json` | Number of records and loss statistics |
| `search_history.csv` | Full parameter-search history |
| `parameter_correlation.csv` | Correlation matrix for loss and searched parameters |
| `fit_records.csv` | Per-record losses |
| `fit_preview.png` | Side-by-side target/generated preview |

## Important limitation

Calibration improves similarity to the selected archive under a simplified one-dimensional model. It does not prove physical equivalence to a proprietary generator, field measurement system, or high-fidelity numerical solver. Archives may provide metadata through the filename convention or through an external metadata CSV, but automatic inference of defect parameters from unlabeled images is outside the current scope.


## Loss-weight sensitivity example

The repository includes `examples/run_loss_weight_sensitivity.py`, which creates a small shifted demo archive and runs compact calibration examples with several pixel/trace weighting ratios. The script writes `outputs/loss_weight_sensitivity.csv` by default and is intended as a lightweight diagnostic for documentation and reproducibility.
