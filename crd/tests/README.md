# CRD Core Tests

This directory contains unit tests for the core modules of the Content Research Digest (CRD) application.

## Running Tests

To run all tests, navigate to the project's root directory (`crd/`) and run:

```bash
python -m unittest discover crd/crd/tests
```

## Test Files

- `test_cli.py`: Tests for the command-line interface (`cli.py`).
- `test_fetcher.py`: Tests for the article fetching logic (`fetcher.py`).
- `test_renderer.py`: Tests for the newsletter rendering logic (`renderer.py`).

Each test file uses Python's `unittest` framework and `unittest.mock` to isolate components and test them independently.