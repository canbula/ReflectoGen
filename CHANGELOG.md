# Changelog

## v1.0.1 - reviewer-response code updates

- Added optional metadata CSV support for calibration archives with inconsistent filenames.
- Added the `profile` subcommand for reflectogram generation from user-defined `z_m`/`area_m2` profiles.
- Added user-adjustable `--pixel-weight` and `--trace-weight` calibration loss weights.
- Added `parameter_correlation.csv` as a lightweight identifiability diagnostic for calibration searches.
- Added `examples/run_sanity_checks.py` for controlled response-behavior checks.
- Added `examples/run_loss_weight_sensitivity.py` for lightweight calibration-loss weight sensitivity checks.
- Updated README and calibration documentation with a fully runnable demo archive workflow.
- Added development-tool recommendations for black, isort, and pylint in `requirements-dev.txt`.

## v1.0.0 - manuscript release candidate

- Added single-case reflectogram generation through the `one` command.
- Added batch generation from CSV parameter tables through the `batch` command.
- Added CSV template creation through the `template` command.
- Added archive-based calibration through the `calibrate` command.
- Added optional waveform and axial area-profile CSV exports.
- Added JSON metadata sidecars and batch manifests.
- Added an example calibrated configuration in `best_config.json`.
- Added packaging metadata, citation metadata, examples, tests, and SoftwareX submission support files.
