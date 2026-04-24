# Contributing

Thank you for your interest in ReflectoGen.

## Development setup

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -e .
pytest -q
```

## Basic expectations

- Keep the core generator dependency-light.
- Prefer explicit parameters and reproducible command-line examples.
- Add or update tests for changes to parsing, generation, rendering, or calibration behavior.
- Keep generated images, sidecar files, and calibration outputs out of version control unless they are intentionally added as small examples.

## Reporting issues

When reporting an issue, include:

- Python version and operating system,
- ReflectoGen version or commit hash,
- exact command used,
- input CSV or filename pattern when relevant,
- traceback or output files needed to reproduce the behavior.
