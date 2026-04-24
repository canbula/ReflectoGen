# ReflectoGen

**ReflectoGen** is a calibration-enabled, physics-inspired Python package for generating synthetic reflectograms for **low-strain pile integrity testing (LSPIT)**.

The package implements a transparent one-dimensional impedance-change model, renders synthetic traces as grayscale PNG reflectograms, exports optional waveform/profile CSV files, and includes an archive-based calibration workflow for fitting selected global generator parameters to existing reflectogram collections.

> ReflectoGen is not a proprietary PIT-S reproduction. It is an open, transparent, physics-inspired generator designed to produce controllable LSPIT-like synthetic reflectograms for research, benchmarking, and education.

## Main features

- Generate synthetic LSPIT reflectogram images from explicit defect parameters.
- Support `Rectangular`, `Round`, and `Triangular` defect-envelope families.
- Model local cross-sectional changes as signed percentage variations.
- Use a simplified one-dimensional impedance-change formulation.
- Convert impedance changes into reflection impulses and two-way travel times.
- Convolve reflection impulses with a Ricker source wavelet.
- Apply time-domain attenuation and toe reflection.
- Render normalized signals as grayscale reflectogram images.
- Save optional waveform CSV and axial area-profile CSV sidecars.
- Generate datasets from a parameter CSV file.
- Calibrate global generator parameters against existing reflectogram archives stored in folders or ZIP files.
- Export calibration summaries, search histories, per-record losses, and fit-preview images.

## Repository contents

```text
ReflectoGen/
├── reflectogen.py                  # Core module and CLI
├── best_config.json                # Example calibrated generator configuration
├── README.md                       # Project overview and usage guide
├── LICENSE                         # MIT license
├── CITATION.cff                    # Citation metadata for GitHub/Zenodo
├── pyproject.toml                  # Optional package metadata and CLI entry point
├── requirements.txt                # Runtime dependencies
├── requirements-dev.txt            # Development/test dependencies
├── examples/
│   ├── params.csv                  # Batch-generation template example
│   ├── example_commands.sh         # Copy-pasteable CLI workflow
│   └── make_demo_archive.py        # Creates a small demo archive for calibration tests
├── tests/
│   └── test_generator_smoke.py     # Minimal import, CLI, and calibration smoke tests
├── docs/
│   ├── API_REFERENCE.md
│   ├── CALIBRATION.md
│   ├── RELEASE_CHECKLIST.md
│   ├── SOFTWAREX_METADATA.md
│   ├── SOFTWAREX_SUBMISSION_SNIPPETS.md
│   └── highlights.txt
└── outputs/
    └── .gitkeep                    # Placeholder for local outputs
```

## Installation

Clone the repository and install the runtime dependencies:

```bash
git clone https://github.com/canbula/ReflectoGen.git
cd ReflectoGen
python -m pip install -r requirements.txt
```

For development and tests:

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -e .
pytest -q
```

The core generator requires:

- Python 3.10 or later
- NumPy
- Pillow

## Command-line interface

ReflectoGen provides four subcommands:

```bash
python reflectogen.py template
python reflectogen.py one
python reflectogen.py batch
python reflectogen.py calibrate
```

After editable installation, the console entry point can also be used:

```bash
reflectogen --version
reflectogen template --out outputs/params.csv
```

## 1. Create a parameter CSV template

```bash
python reflectogen.py template --out outputs/params.csv
```

This writes a minimal CSV file with the required columns:

```csv
shape,start_m,end_m,percent_change
Rectangular,10.0,10.5,-20
Round,15.0,15.5,12
Rectangular,20.0,21.0,-35
```

## 2. Generate one reflectogram

```bash
python reflectogen.py one \
  --shape Rectangular \
  --start 10.0 \
  --end 10.5 \
  --percent -20 \
  --out outputs/Rectangular_10.0_10.5_-20.png
```

Optional waveform and area-profile exports:

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

A single-case run can produce:

- `*.png` reflectogram image
- `*.meta.json` case metadata and generator configuration
- `*.signal.csv` waveform file, when requested
- `*.profile.csv` axial area-profile file, when requested

## 3. Batch generation from CSV

```bash
python reflectogen.py batch \
  --csv examples/params.csv \
  --out-dir outputs/generated_reflectograms \
  --save-signal-csv \
  --save-profile-csv
```

The batch command writes one PNG reflectogram per CSV row, optional sidecar CSV files, and `manifest.json`.

## 4. Calibration against an existing archive

Calibration fits selected global generator parameters to an existing reflectogram archive. The archive can be a folder or ZIP file containing images whose filenames follow the required naming convention.

```bash
python reflectogen.py calibrate \
  --input legacy_reflectograms.zip \
  --out outputs/calibration_run \
  --max-images 250 \
  --stages 3 \
  --trials-per-stage 80 \
  --seed 42
```

Calibration outputs include:

| Output | Description |
|---|---|
| `best_config.json` | Best calibrated generator configuration |
| `fit_summary.json` | Summary of calibration loss statistics |
| `search_history.csv` | Full parameter-search history |
| `fit_records.csv` | Per-record calibration losses |
| `fit_preview.png` | Side-by-side target/generated preview |

## Use a calibrated configuration

The repository includes an example calibrated configuration in `best_config.json`. To generate with that configuration:

```bash
python reflectogen.py one \
  --shape Rectangular \
  --start 10.0 \
  --end 10.5 \
  --percent -20 \
  --out outputs/calibrated_case.png \
  --config-json best_config.json
```

The same configuration can be used in batch mode:

```bash
python reflectogen.py batch \
  --csv examples/params.csv \
  --out-dir outputs/generated_calibrated \
  --config-json best_config.json
```

## Calibration filename convention

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

Negative values represent local section loss; positive values represent local section increase.

## Python API example

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

## Calibration loss

The calibration loss combines pixel-level mean squared error and trace-centerline mean squared error:

```text
loss = 0.35 × pixel_mse + 0.65 × trace_mse
```

The trace term is weighted more strongly to emphasize waveform trajectory agreement.

## Minimal smoke test

```bash
python reflectogen.py one \
  --shape Rectangular \
  --start 10.0 \
  --end 10.5 \
  --percent -20 \
  --out outputs/test_reflectogram.png
```

The command should create:

```text
outputs/test_reflectogram.png
outputs/test_reflectogram.meta.json
```

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

## Limitations

- The software uses a simplified one-dimensional impedance-based formulation.
- It does not reproduce proprietary commercial software exactly.
- It does not replace field validation or high-fidelity numerical simulation.
- Calibration improves similarity to a given archive but does not guarantee physical equivalence.
- Generated reflectograms should be interpreted as controlled synthetic research data.

## Citation

If you use ReflectoGen in a publication, please cite the archived software release and the associated SoftwareX article when available. Citation metadata are provided in `CITATION.cff`.

```bibtex
@software{canbula_reflectogen_2026,
  title     = {ReflectoGen: Physics-Inspired and Calibration-Enabled Reflectogram Synthesis for Pile Integrity Testing},
  author    = {Canbula, Bora and Öztürk, Övünç and Özacar, Vehbi and Özacar, Tuğba},
  year      = {2026},
  version   = {1.0.0},
  publisher = {Zenodo},
  url       = {https://github.com/canbula/ReflectoGen}
}
```

Replace the citation URL/DOI with the Zenodo DOI after archiving the `v1.0.0` release.

## License

ReflectoGen is released under the MIT License. See `LICENSE`.

## Acknowledgements

ReflectoGen was developed to support open, reproducible generation of synthetic reflectograms for low-strain pile integrity testing research, especially in workflows involving benchmark construction and machine-learning evaluation.
