# AGENTS.md

## Project Overview

A 7-Zip frontend application built with Python. Automatically extracts password-protected archives using a user-saved password list.

### Core Features
- Manage user-saved passwords (plain text JSON storage)
- Accept user input for archive file paths
- Automatically attempt extraction with saved passwords
- Report extraction results to the user

## Tech Stack

- **Language**: Python 3.10+
- **Archive Backend**: Bundled 7-Zip executable (`autopasstryunzip/lib/win-x64/7z.exe`)
- **Password Storage**: JSON file in user data directory (`%APPDATA%/autoPassTryUnzip/passwords.json` on Windows)
- **Interface**: CLI (command: `autopass-unzip`)
- **Platform**: Windows x64 only (Linux/macOS support prepared)

## Supported Formats

- `.7z` - 7-Zip archive
- `.zip` - ZIP archive
- `.rar` - RAR archive

## Project Structure

```
autoPassTryUnzip/
├── autopasstryunzip/          # Main Python package
│   ├── __init__.py
│   ├── __main__.py            # Entry point for `python -m autopasstryunzip`
│   ├── main.py                # CLI entry point with argparse
│   ├── password_manager.py    # Password storage and management
│   ├── extractor.py           # 7-Zip extraction logic
│   ├── utils.py               # Custom exceptions and helpers
│   └── lib/
│       └── win-x64/
│           └── 7z.exe         # Bundled 7-Zip executable
├── tests/
│   ├── __init__.py
│   ├── test_cli.py
│   ├── test_password_manager.py
│   └── test_extractor.py
├── docs/                      # Sphinx documentation
│   ├── conf.py                # Sphinx configuration
│   ├── index.rst              # Documentation homepage
│   ├── modules.rst            # API module index
│   ├── Makefile               # Build commands
│   └── _static/               # Static assets
├── pyproject.toml             # Package configuration
├── MANIFEST.in                # Package data includes
├── requirements.txt
├── requirements-dev.txt
├── README.md
└── AGENTS.md
```

## Development Guidelines

### Code Style
- Follow PEP 8 conventions
- Use type hints for all function signatures (use `X | None` syntax)
- Use f-strings for string formatting
- Maximum line length: 100 characters
- Use descriptive variable and function names

### Imports Order
1. Standard library
2. Third-party libraries
3. Local modules

Example:
```python
import subprocess
from pathlib import Path

from autopasstryunzip.utils import ExtractionError
```

### Error Handling
- Use custom exceptions from `autopasstryunzip.utils`:
  - `AutoPassError` - base exception
  - `PasswordManagerError` - password management errors
  - `ExtractionError` - extraction errors
  - `InvalidArchiveError` - invalid archive errors
  - `PasswordNotFoundError` - no matching password
- Provide meaningful error messages to users

### Platform Paths

Use helper functions from `utils.py`:
- `get_user_data_dir()` - Platform-specific user data directory for passwords
- `get_package_root()` - Package directory (contains bundled 7z.exe)

### Testing
- Use pytest as the testing framework
- Place test files in the `tests/` directory
- Use `tempfile.TemporaryDirectory` for test fixtures
- Tests use bundled 7z.exe to create test archives

### Dependencies
- Production: None (uses bundled 7-Zip)
- Development: `pytest`, `ruff`, `mypy`, `sphinx`, `sphinx-rtd-theme`, `sphinx-autodoc-typehints`

### Documentation
- All public modules, classes, and functions must have Google-style docstrings
- Docstrings are used to auto-generate API documentation via Sphinx
- Keep docstrings up-to-date when modifying function signatures or behavior
- Use type hints - they are automatically included in the documentation

## Installation

```bash
pip install .
```

After installation, the `autopass-unzip` CLI command is available globally.

## Commands

### Run Application (Installed)
```bash
autopass-unzip <command> [options]

# Global Options:
#   -h, --help                            Show help message and exit
#   -v, --version                         Show version information and exit

# Commands:
#   add <password> [<password> ...]       Add password(s)
#   remove [-i N [N ...]] [<password> ...]  Remove by value(s) or index
#   list                                  List stored passwords (with 1-based index)
#   path                                  Show passwords file path
#   edit                                  Open passwords file in default editor
#   clear [-f]                            Clear all passwords
#   extract <archive>                     Extract an archive
```

### Run Application (Development)
```bash
python -m autopasstryunzip <command> [options]
```

### Run Tests
```bash
pytest
```

### Run Linting
```bash
ruff check .
```

### Run Type Checking
```bash
mypy autopasstryunzip/
```

### Build Package

**Standard build:**
```bash
python -m build
```

**Full build (clean build):**
When updating bundled binaries (e.g., 7-Zip), use a full build to ensure pip does not use cached files from previous builds:

```bash
# Clean previous build artifacts
rm -r build dist *.egg-info

# Reinstall without cache
pip install . --no-cache-dir --force-reinstall
```

**Why full build is needed:**
`setuptools` caches build artifacts in the `build/` directory. When updating bundled binaries (like `7z.exe` or `7z.dll`), a standard `pip install .` may reuse the cached versions from `build/lib/`, resulting in the old binaries being installed. Always perform a full build after modifying bundled resources.

**Quick check after installation:**
```bash
autopass-unzip -v
# Should show: Using 7-Zip binary: 7-Zip 24.09 (x64) ...
```

### Build Documentation
```bash
# Generate HTML documentation (output: docs/_build/html/)
sphinx-build -b html docs docs/_build/html

# Or use the Makefile
cd docs
make html
```

### View Documentation
Open `docs/_build/html/index.html` in a web browser after building.

## AI Agent Instructions

### When Adding New Features
1. Follow the existing project structure
2. Add appropriate type hints using `X | None` syntax
3. Write tests for new functionality
4. Update documentation if needed

### When Fixing Bugs
1. Add a test case that reproduces the bug
2. Fix the bug
3. Ensure all tests pass

### When Refactoring
1. Ensure existing tests pass before refactoring
2. Run tests after refactoring to verify behavior
3. Maintain backward compatibility for public APIs

## Notes

- Supports `.7z`, `.zip`, `.rar` formats via bundled 7-Zip
- Passwords are stored in plain text in the user data directory (platform-specific)
- 7-Zip is licensed under GNU LGPL (see README.md for details)
