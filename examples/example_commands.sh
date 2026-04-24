#!/usr/bin/env bash
set -euo pipefail

# Run from the repository root.

python reflectogen.py --version

python reflectogen.py template \
  --out outputs/params.csv

python reflectogen.py one \
  --shape Rectangular \
  --start 10.0 \
  --end 10.5 \
  --percent -20 \
  --out outputs/Rectangular_10.0_10.5_-20.png \
  --save-signal-csv \
  --save-profile-csv

python reflectogen.py batch \
  --csv examples/params.csv \
  --out-dir outputs/generated_reflectograms \
  --save-signal-csv \
  --save-profile-csv

python examples/make_demo_archive.py \
  --out outputs/demo_legacy_reflectograms.zip

python reflectogen.py calibrate \
  --input outputs/demo_legacy_reflectograms.zip \
  --out outputs/calibration_demo \
  --max-images 6 \
  --stages 1 \
  --trials-per-stage 3 \
  --seed 42

python reflectogen.py batch \
  --csv examples/params.csv \
  --out-dir outputs/generated_calibrated \
  --config-json outputs/calibration_demo/best_config.json
