# AGENTS Instructions

This project uses the style configuration defined in `pyproject.toml`. Please follow these guidelines when contributing code:

- Target Python version is 3.11.
- Use Ruff for linting and formatting.
- Formatting rules:
  - Maximum line length is 100 characters.
  - Use double quotes for strings.
  - Use spaces for indentation.
  - Docstring code formatting is enabled.
- Linting rules:
  - Enable rule sets: E, F, I, UP.
  - Allow `F401` in `__init__.py` files for re-exports.
  - Allow `E501` in files under `migrations/`.

Ensure commits keep the codebase compliant with these conventions.
