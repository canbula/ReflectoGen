# ReflectoGen

**ReflectoGen** is a calibration-enabled, physics-inspired Python package for generating synthetic reflectograms for **low-strain pile integrity testing (LSPIT)**.

The package implements a transparent one-dimensional impedance-change model, renders synthetic traces as grayscale PNG reflectograms, exports optional waveform/profile CSV files, and includes an archive-based calibration workflow for fitting selected global generator parameters to existing reflectogram collections.

> ReflectoGen is not a proprietary PIT-S reproduction. It is an open, transparent, physics-inspired generator designed to produce controllable LSPIT-like synthetic reflectograms for research, benchmarking, and education.

## Main features

- Generate synthetic LSPIT reflectogram images from explicit defect parameters.
- Generate reflectograms from user-defined axial area-profile CSV files.
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
│   ├── example_area_profile.csv    # User-defined area-profile example
│   ├── example_commands.sh         # Copy-pasteable CLI workflow
│   ├── make_demo_archive.py        # Creates a small demo archive for calibration tests
│   ├── run_sanity_checks.py        # Controlled response-behavior checks
│   └── run_loss_weight_sensitivity.py # Lightweight calibration-loss weighting check
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

ReflectoGen provides five subcommands. The following lines show the available subcommands only; each subcommand requires its own arguments, as shown in the complete runnable examples below.

```bash
python reflectogen.py template --help
python reflectogen.py one --help
python reflectogen.py batch --help
python reflectogen.py profile --help
python reflectogen.py calibrate --help
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


## 4. Generation from a user-defined area profile

For irregular or multi-anomaly cases, ReflectoGen can synthesize a reflectogram directly from an axial area-profile CSV instead of using the built-in rectangular, round, or triangular envelopes. The CSV must contain `z_m` and `area_m2` columns:

```csv
z_m,area_m2
0.0,0.1963495
10.0,0.1963495
10.5,0.1500000
11.0,0.1963495
30.0,0.1963495
```

Run:

```bash
python reflectogen.py profile \
  --profile-csv examples/example_area_profile.csv \
  --out outputs/profile_case.png \
  --save-signal-csv \
  --save-profile-csv
```

This mode exposes the internal impedance engine for user-defined `z`--`A(z)` profiles and is intended for cases where a simple parametric envelope is too restrictive.

## 5. Calibration against an existing archive

Calibration fits selected global generator parameters to an existing reflectogram archive. The archive can be a folder or ZIP file. By default, metadata are parsed from filenames, but an optional metadata CSV can also be supplied for archives whose filenames do not encode the defect parameters.

### Reproducible demo calibration workflow

The repository does not require an external legacy archive to run a calibration smoke test. First create a small demo archive, then use it as the calibration input:

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

For a larger external archive, use the same command pattern and replace the `--input` path with your own folder or ZIP file.

Calibration outputs include:

| Output | Description |
|---|---|
| `best_config.json` | Best calibrated generator configuration |
| `fit_summary.json` | Summary of calibration loss statistics |
| `search_history.csv` | Full parameter-search history |
| `parameter_correlation.csv` | Lightweight correlation diagnostic for searched parameters and loss |
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

## Calibration metadata

### Filename convention

Existing reflectograms used for calibration can follow this filename format:

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

### Optional metadata CSV

If filenames are inconsistent, calibration metadata can be supplied with `--metadata-csv`. The CSV must contain either `filename` or `relative_path`, plus `shape`, `start_m`, `end_m`, and `percent_change`:

```csv
filename,shape,start_m,end_m,percent_change
case_001.png,Rectangular,10.0,10.5,-20
case_002.png,Round,15.0,15.5,12
```

Example:

```bash
python reflectogen.py calibrate \
  --input legacy_archive.zip \
  --metadata-csv legacy_metadata.csv \
  --out outputs/calibration_with_metadata \
  --max-images 250 \
  --stages 3 \
  --trials-per-stage 80
```

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
loss = (pixel_weight × pixel_mse + trace_weight × trace_mse) / (pixel_weight + trace_weight)
```

The default weights are `pixel_weight = 0.35` and `trace_weight = 0.65`. The trace term is weighted more strongly to emphasize waveform trajectory agreement rather than background-pixel overlap. The weights can be changed from the command line:

```bash
python reflectogen.py calibrate \
  --input outputs/demo_legacy_reflectograms.zip \
  --out outputs/calibration_trace_weighted \
  --pixel-weight 0.25 \
  --trace-weight 0.75
```


## Calibration weight sensitivity example

The default calibration loss uses `pixel_weight = 0.35` and `trace_weight = 0.65`. To help users inspect how different weighting choices affect a compact calibration example, run:

```bash
python examples/run_loss_weight_sensitivity.py \
  --out outputs/loss_weight_sensitivity.csv \
  --stages 1 \
  --trials-per-stage 20
```

The script creates a small shifted demo archive and writes a CSV table comparing several pixel/trace weighting pairs. It is intended as a lightweight sensitivity diagnostic rather than as a physical validation experiment.

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

## Sanity-check examples

The `examples/run_sanity_checks.py` script generates a compact CSV table showing how simple response descriptors change under controlled variations of defect location, length, sign, and magnitude:

```bash
python examples/run_sanity_checks.py --out outputs/sanity_checks.csv
```

The script is intended as a lightweight reproducibility and plausibility check, not as field validation.

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
- Metadata can be supplied by filename convention or metadata CSV; automatic inference of defect parameters from unlabeled images is outside the current scope.
- Generated reflectograms should be interpreted as controlled synthetic research data.

## Citation

If you use ReflectoGen in a publication, please cite the archived software release and the associated SoftwareX article when available. Citation metadata are provided in `CITATION.cff`.

```bibtex
@article{REFLECTOGEN2026,
title = {ReflectoGen: Physics-inspired and calibration-enabled reflectogram synthesis for pile integrity testing},
journal = {SoftwareX},
volume = {35},
pages = {102817},
year = {2026},
issn = {2352-7110},
doi = {https://doi.org/10.1016/j.softx.2026.102817},
url = {https://www.sciencedirect.com/science/article/pii/S2352711026003092},
author = {Bora Canbula and Övünç Öztürk and Vehbi Özacar and Tuğba Özacar},
keywords = {Low-strain pile integrity testing, Synthetic reflectogram generation, Calibration-enabled software, Physics-inspired modeling, Python scientific software, Benchmark data generation},
abstract = {ReflectoGen is a calibration-enabled Python software package for synthetic reflectogram generation in low-strain pile integrity testing (LSPIT). The software implements a physics-inspired one-dimensional impedance-based formulation in which local cross-sectional variations are converted into reflection impulses, convolved with a Ricker source wavelet, attenuated in time, normalized, and rendered as grayscale reflectograms. Rectangular, round, and triangular defect morphologies are supported, and the software can generate single cases, batch datasets, waveform CSV files, and section-profile CSV files through a command-line workflow. To support reuse of legacy datasets when proprietary tools are unavailable, ReflectoGen also provides a calibration module that fits global parameters against existing reflectogram archives stored in folders or archive files, using either filename-derived or metadata-CSV-derived defect descriptions together with a combined image- and trace-based similarity criterion. The revised release also exposes configurable calibration-loss weights, writes a parameter-correlation diagnostic, and includes lightweight sanity-check scripts for controlled changes in defect position, length, sign, and magnitude. The software is intended for synthetic benchmark construction, ablation studies, machine-learning dataset generation, and reproducible method development in pile integrity assessment. By combining transparent parameter control with archive-based calibration, ReflectoGen provides a practical and extensible framework for generating synthetic LSPIT reflectograms when access to proprietary generation tools is limited.}
}

```

## License

ReflectoGen is released under the MIT License. See `LICENSE`.

## Acknowledgements

ReflectoGen was developed to support open, reproducible generation of synthetic reflectograms for low-strain pile integrity testing research, especially in workflows involving benchmark construction and machine-learning evaluation.
