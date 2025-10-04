# Test Validation Scripts

Ad-hoc validation and testing scripts used during development.

**Note**: These are NOT pytest tests. They are standalone validation scripts for manual testing and experimentation.

## Purpose

These scripts were created for:
- One-off validation of specific features
- Manual integration testing during development
- Performance benchmarking
- Component isolation testing

## Running Scripts

```bash
export PYTHONPATH=.
python scripts/testing/test_element_tracer.py
```

## Difference from `tests/`

- **`tests/`** - Formal pytest test suite (run with `pytest`)
- **`scripts/testing/`** - One-off validation scripts (run directly with `python`)

The formal test suite in `tests/` should be used for CI/CD and regular testing. These scripts are for development and debugging.

## Organization

Scripts are named by feature area:
- `test_*_integration.py` - Integration validation
- `test_*_e2e.py` - End-to-end validation
- `test_task*.py` - Task-specific validation

**Last Updated**: 2025-10-03
