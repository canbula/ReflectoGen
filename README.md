# ReflectoGen

**SoftwareX manuscript title:** *ReflectoGen: Physics-Inspired and Calibration-Enabled Reflectogram Synthesis for Pile Integrity Testing*

**ReflectoGen** is a calibration-enabled, physics-inspired Python software package for generating synthetic reflectograms for **low-strain pile integrity testing (LSPIT)**. It provides a transparent one-dimensional impedance-based reflectogram generator, supports parameter-controlled defect envelopes, and includes a calibration workflow for fitting global generator parameters to existing reflectogram archives.

The software is intended for synthetic benchmark construction, ablation studies, machine-learning dataset generation, reproducible method development, and educational use in pile integrity assessment.

> ReflectoGen is not a proprietary PIT-S reproduction. It is an open, transparent, physics-inspired generator designed to produce controllable synthetic LSPIT-like reflectograms.

---

## Main features

- Generate synthetic LSPIT reflectogram images from explicit defect parameters.
- Support three defect-envelope families:
  - `Rectangular`
  - `Round`
  - `Triangular`
- Model local cross-sectional changes as signed percentage variations.
- Use a simplified one-dimensional impedance-change formulation.
- Convert impedance changes into reflection impulses.
- Convolve reflection impulses with a Ricker source wavelet.
- Apply time-domain attenuation and toe reflection.
- Render normalized signals as grayscale reflectogram images.
- Save optional waveform and section-profile CSV files.
- Generate large datasets from a parameter CSV file.
- Calibrate global generator parameters against existing reflectogram archives stored in folders or ZIP files.
- Export calibration summaries, search histories, per-record losses, and fit-preview images.

---

## Installation

Clone the repository and install the required Python packages:

```bash
pip install numpy pillow
```

Optional GUI components may require additional packages such as `PySide6` if the graphical interface is used:

```bash
pip install PySide6
```

The core generator itself requires only:

- Python 3.10+
- NumPy
- Pillow

---

## File naming convention

Existing reflectograms used for calibration must follow this filename format:

```text
Shape_start_m_end_m_percent_change.png
```

Examples:

```text
Rectangular_10.0_10.5_-20.png
Round_15.0_15.5_12.png
Triangular_20.0_21.0_-35.png
```

The filename is parsed as:

| Field | Meaning |
|---|---|
| `Shape` | Defect-envelope family |
| `start_m` | Defect start location in meters |
| `end_m` | Defect end location in meters |
| `percent_change` | Signed cross-sectional change in percent |

Negative values represent local section loss; positive values represent local section increase.

---

## Command-line interface

ReflectoGen provides four subcommands:

```bash
python reflectogen.py template
python reflectogen.py one
python reflectogen.py batch
python reflectogen.py calibrate
```

---

## 1. Create a parameter CSV template

```bash
python reflectogen.py template --out params.csv
```

This creates a minimal CSV file with the required columns:

```csv
shape,start_m,end_m,percent_change
Rectangular,10.0,10.5,-20
Round,15.0,15.5,12
Rectangular,20.0,21.0,-35
```

---

## 2. Generate one reflectogram

```bash
python reflectogen.py one \
  --shape Rectangular \
  --start 10.0 \
  --end 10.5 \
  --percent -20 \
  --out outputs/Rectangular_10.0_10.5_-20.png
```

Optional outputs:

```bash
python reflectogen.py one \
  --shape Round \
  --start 12.0 \
  --end 12.5 \
  --percent 15 \
  --out outputs/Round_12.0_12.5_15.png \
  --save-signal-csv \
  --save-profile-csv
```

This can produce:

- `*.png` reflectogram image
- `*.signal.csv` waveform file
- `*.profile.csv` axial area-profile file
- `*.meta.json` metadata and generator configuration file

---

## 3. Batch generation from a CSV file

```bash
python reflectogen.py batch \
  --csv params.csv \
  --out-dir generated_reflectograms
```

With optional signal and profile exports:

```bash
python reflectogen.py batch \
  --csv params.csv \
  --out-dir generated_reflectograms \
  --save-signal-csv \
  --save-profile-csv
```

The batch command writes:

- one PNG reflectogram per CSV row
- optional signal/profile CSV files
- `manifest.json` describing all generated cases

---

## 4. Calibration against an existing archive

The calibration command fits selected global generator parameters to an existing reflectogram archive. The archive can be a folder or a ZIP file containing reflectogram images whose filenames follow the required naming convention.

```bash
python reflectogen.py calibrate \
  --input reflectograms.zip \
  --out calibration_outputs \
  --max-images 250 \
  --stages 3 \
  --trials-per-stage 80 \
  --seed 42
```

The calibration workflow:

1. Loads reflectogram images from a directory or ZIP archive.
2. Parses defect metadata from filenames.
3. Evaluates the default generator configuration.
4. Performs staged random search with local refinement.
5. Selects the configuration that minimizes a combined image and trace similarity loss.
6. Exports calibration diagnostics and preview images.

Calibration outputs include:

| Output | Description |
|---|---|
| `best_config.json` | Best calibrated generator configuration |
| `fit_summary.json` | Summary of calibration loss statistics |
| `search_history.csv` | Full parameter-search history |
| `fit_records.csv` | Per-record calibration losses |
| `fit_preview.png` | Side-by-side target and generated preview |

---

## Use a calibrated configuration

After calibration, generated reflectograms can use the fitted configuration:

```bash
python reflectogen.py one \
  --shape Rectangular \
  --start 10.0 \
  --end 10.5 \
  --percent -20 \
  --out outputs/calibrated_case.png \
  --config-json calibration_outputs/best_config.json
```

The same configuration can be used in batch mode:

```bash
python reflectogen.py batch \
  --csv params.csv \
  --out-dir generated_calibrated \
  --config-json calibration_outputs/best_config.json
```

---

## Generator configuration

The generator is controlled by the `GeneratorConfig` dataclass.

| Parameter | Default | Description |
|---|---:|---|
| `pile_length_m` | `30.0` | Pile length in meters |
| `pile_diameter_m` | `0.50` | Pile diameter in meters |
| `wave_speed_m_s` | `3900.0` | Longitudinal wave speed |
| `density_kg_m3` | `2450.0` | Material density |
| `toe_reflection_coeff` | `0.85` | Toe reflection coefficient |
| `damping_alpha` | `45.0` | Exponential time-domain damping parameter |
| `dz_m` | `0.01` | Spatial discretization along pile axis |
| `oversample_factor` | `8` | Oversampling factor before downsampling |
| `n_samples` | `2048` | Number of final signal samples |
| `f0_hz` | `2500.0` | Ricker wavelet central frequency |
| `t_margin_factor` | `1.20` | Time-window extension beyond toe arrival |
| `source_amplitude` | `1.0` | Source pulse amplitude |
| `source_delay_s` | `0.00025` | Source pulse delay in seconds |
| `render_width` | `300` | Output image width in pixels |
| `render_height` | `100` | Output image height in pixels |
| `line_width` | `2` | Rendered trace line width |
| `background` | `255` | Grayscale background value |
| `foreground` | `0` | Grayscale trace value |
| `vertical_margin_px` | `6` | Vertical rendering margin |

---

## Calibration parameter ranges

During calibration, the random search varies the following parameters:

| Parameter | Search range |
|---|---:|
| `wave_speed_m_s` | `3200.0` – `4700.0` |
| `toe_reflection_coeff` | `0.35` – `1.25` |
| `damping_alpha` | `8.0` – `95.0` |
| `f0_hz` | `1000.0` – `4200.0` |
| `source_delay_s` | `0.00005` – `0.00060` |
| `t_margin_factor` | `1.00` – `1.45` |
| `line_width` | `1` – `3` |
| `vertical_margin_px` | `3` – `12` |

The calibration loss combines:

- pixel-level mean squared error, and
- trace-centerline mean squared error.

The implemented loss is:

```text
loss = 0.35 × pixel_mse + 0.65 × trace_mse
```

The trace term is weighted more strongly to emphasize waveform trajectory agreement.

---

## Python API example

The package can also be used as an importable Python module:

```python
from reflectogen import GeneratorConfig, synthesize_signal, render_reflectogram

cfg = GeneratorConfig()

time_s, signal, z_m, area_m2 = synthesize_signal(
    cfg,
    shape="Rectangular",
    start_m=10.0,
    end_m=10.5,
    percent_change=-20,
)

img = render_reflectogram(cfg, signal)
img.save("Rectangular_10.0_10.5_-20.png")
```

To obtain a normalized image array directly:

```python
from reflectogen import GeneratorConfig, generate_image_array

cfg = GeneratorConfig()
arr = generate_image_array(cfg, "Round", 15.0, 15.5, 12)
```

---

## Software architecture

The software is organized around the following functional blocks:

| Block | Main functions |
|---|---|
| Filename parsing | `parse_filename` |
| Defect envelope construction | `_shape_envelope` |
| Area-profile construction | `build_area_profile` |
| Reflection-event computation | `compute_reflection_impulses` |
| Source wavelet | `ricker_wavelet` |
| Signal synthesis | `synthesize_signal` |
| Image rendering | `render_reflectogram` |
| Batch generation | `cmd_batch` |
| Calibration | `cmd_calibrate`, `evaluate_config`, `sample_random_config` |
| Diagnostics | `image_distance`, `trace_from_image`, `make_preview` |
| CLI | `build_parser`, `main` |

---

## Example workflow

A typical complete workflow is:

```bash
# 1. Write a CSV template
python reflectogen.py template --out params.csv

# 2. Generate an initial synthetic dataset
python reflectogen.py batch \
  --csv params.csv \
  --out-dir generated_reflectograms \
  --save-signal-csv \
  --save-profile-csv

# 3. Calibrate against an existing archive
python reflectogen.py calibrate \
  --input legacy_reflectograms.zip \
  --out calibration_outputs \
  --max-images 300 \
  --stages 3 \
  --trials-per-stage 120

# 4. Generate a calibrated dataset
python reflectogen.py batch \
  --csv params.csv \
  --out-dir generated_calibrated \
  --config-json calibration_outputs/best_config.json
```

---

## Outputs and file products

Depending on the selected command and options, ReflectoGen can produce:

- grayscale PNG reflectograms,
- normalized signal CSV files,
- axial section-profile CSV files,
- metadata JSON files,
- batch manifests,
- calibration summaries,
- calibration search histories,
- per-record fit diagnostics,
- side-by-side fit previews.

---

## Intended applications

ReflectoGen is designed for:

- synthetic LSPIT reflectogram generation,
- machine-learning dataset construction,
- controlled benchmark design,
- ablation studies,
- synthetic pretraining,
- model stress testing,
- educational demonstrations of pile integrity response behavior,
- reproducible method development when proprietary generation tools are unavailable.

---

## Limitations

- The software uses a simplified one-dimensional impedance-based formulation.
- It does not reproduce proprietary commercial software exactly.
- It does not replace field validation or high-fidelity numerical simulation.
- Calibration improves similarity to a given archive but does not guarantee physical equivalence.
- Generated reflectograms should be interpreted as controlled synthetic research data.

---

## Recommended repository structure

```text
ReflectoGen/
├── reflectogen.py
├── README.md
├── requirements.txt
├── examples/
│   ├── params.csv
│   └── example_commands.sh
├── docs/
│   └── softwarex_manuscript.md
├── outputs/
│   └── .gitkeep
└── tests/
    └── test_generator_smoke.py
```

---

## Minimal smoke test

```bash
python reflectogen.py one \
  --shape Rectangular \
  --start 10.0 \
  --end 10.5 \
  --percent -20 \
  --out test_reflectogram.png
```

The command should create:

```text
test_reflectogram.png
test_reflectogram.meta.json
```

---

## Citation

If you use ReflectoGen in a publication, please cite the associated SoftwareX paper once available.

```bibtex
@software{reflectogen,
  title  = {ReflectoGen: Physics-Inspired and Calibration-Enabled Reflectogram Synthesis for Pile Integrity Testing},
  author = {Bora Canbula, Övünç Öztürk, Vehbi Özacar, and Tuğba Özacar},
  year   = {2026},
  url    = {https://github.com/canbula/ReflectoGen}
}
```

---

## License

```text
MIT License

Copyright (c) 2026 Bora Canbula, Övünç Öztürk, Vehbi Özacar, and Tuğba Özacar

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Acknowledgements

ReflectoGen was developed to support open, reproducible generation of synthetic reflectograms for low-strain pile integrity testing research, especially in workflows involving benchmark construction and machine-learning evaluation.
