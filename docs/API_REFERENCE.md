# API reference

ReflectoGen is currently distributed as a single importable Python module, `reflectogen.py`.

## Configuration and records

### `GeneratorConfig`

Frozen dataclass storing generator and rendering settings.

Important fields include:

- `pile_length_m`, `pile_diameter_m`
- `wave_speed_m_s`, `density_kg_m3`
- `toe_reflection_coeff`, `damping_alpha`
- `dz_m`, `oversample_factor`, `n_samples`
- `f0_hz`, `source_amplitude`, `source_delay_s`
- `render_width`, `render_height`, `line_width`

### `Record`

Frozen dataclass used by calibration. It stores filename-derived defect metadata and the loaded target image array.

## Main generation functions

### `build_area_profile(cfg, shape, start_m, end_m, percent_change)`

Builds an axial cross-sectional area profile from the selected defect envelope.

### `compute_reflection_impulses(cfg, z, area)`

Computes first-order reflection events from adjacent impedance changes and adds the source and toe events.

### `synthesize_signal(cfg, shape, start_m, end_m, percent_change)`

Generates a normalized one-dimensional response signal from a built-in parametric defect envelope and returns:

```python
time_s, signal, z_m, area_m2
```

### `synthesize_signal_from_profile(cfg, z, area)`

Generates a normalized one-dimensional response signal from an arbitrary user-defined axial area profile. This exposes the impedance engine for irregular or multi-anomaly cases.

### `load_area_profile_csv(path)`

Loads a CSV file with `z_m` and `area_m2` columns for the `profile` subcommand.

### `render_reflectogram(cfg, signal)`

Renders a normalized signal as a grayscale `PIL.Image.Image`.

### `generate_image_array(cfg, shape, start_m, end_m, percent_change)`

Returns a normalized grayscale reflectogram array in the `[0, 1]` range.

## Calibration helpers

### `load_metadata_csv(path)`

Loads optional calibration metadata from a CSV file. The CSV must contain either `filename` or `relative_path`, plus `shape`, `start_m`, `end_m`, and `percent_change`.

### `load_records(source, max_images=None, seed=42, metadata_csv=None)`

Loads calibration records from a folder or ZIP archive. If `metadata_csv` is supplied, metadata are read from the CSV first. Otherwise filenames must follow:

```text
Shape_start_m_end_m_percent_change.png
```

### `image_distance(target, pred, pixel_weight=0.35, trace_weight=0.65)`

Computes the calibration loss:

```text
(pixel_weight × pixel_mse + trace_weight × trace_mse) / (pixel_weight + trace_weight)
```

### `evaluate_config(cfg, records, pixel_weight=0.35, trace_weight=0.65)`

Returns mean loss and per-record losses for a candidate generator configuration.

### `sample_random_config(rng, base=None, sigma_scale=1.0)`

Samples a candidate configuration for random or local-refinement search.

### `write_parameter_correlation(history, out_path)`

Writes a lightweight parameter-correlation diagnostic for the searched calibration parameters and the loss.

## Command dispatch

- `cmd_template(args)` writes a parameter CSV template.
- `cmd_one(args)` generates one reflectogram.
- `cmd_batch(args)` generates a dataset from CSV.
- `cmd_profile(args)` generates a reflectogram from a user-defined area-profile CSV.
- `cmd_calibrate(args)` calibrates against an archive.
- `build_parser()` creates the CLI parser.
- `main()` dispatches the selected subcommand.
