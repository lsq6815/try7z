# try7z

A 7-Zip frontend application for automatically extracting password-protected archives using a user-saved password list.

## Features

- Manage password list (add, remove, list, clear)
- Automatically try multiple passwords for archive extraction
- Support for `.7z`, `.zip`, `.rar` formats
- Extract multiple archives in one command
- Bundled 7-Zip executable - no external dependencies
- Built-in benchmark tests for performance monitoring

## Installation

### From Source

```bash
# Clone the repository
git clone <repository-url>
cd try7z

# Create virtual environment (recommended)
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS

# Install the package
pip install .
```

### Full Build (After Updating Bundled Binaries)

If you have updated bundled binaries (e.g., 7-Zip executable or DLLs) and need to reinstall, perform a **full build** to ensure `pip` does not reuse cached build artifacts:

```bash
# Clean previous build artifacts
rm -r build dist *.egg-info

# Reinstall without cache
pip install . --no-cache-dir --force-reinstall
```

**Why this is needed:** `setuptools` caches files in the `build/` directory. Without cleaning, `pip install .` may install old versions of bundled binaries (e.g., an outdated `7z.exe`).

**Verify the correct version is installed:**
```bash
try7z -v
# Should show: Using 7-Zip binary: 7-Zip 24.09 (x64) ...
```

### Development Installation

```bash
pip install -e ".[dev]"
```

## Usage

After installation, use the `try7z` command:

### Password Management

```bash
# Show version information
try7z -v

# Add password(s)
try7z add "my_password"
try7z add "pwd1" "pwd2" "pwd3"  # Add multiple at once

# List stored passwords (shows 1-based index)
try7z list

# Remove password(s) by value
try7z remove "my_password"
try7z remove "pwd1" "pwd2" "pwd3"  # Remove multiple at once

# Remove password(s) by index (from 'list' command)
try7z remove -i 3          # Remove index 3
try7z remove -i 1 5 10     # Remove multiple indices

# Show passwords file path
try7z path

# Open passwords file in default editor
try7z edit

# Clear all passwords (with confirmation)
try7z clear

# Clear all passwords (skip confirmation)
try7z clear -f
```

### Archive Extraction

```bash
# Extract an archive using stored passwords
try7z extract path/to/archive.7z

# Extract multiple archives at once
try7z extract archive1.7z archive2.zip archive3.rar

# Extract with custom output directory
try7z extract path/to/archive.7z -o output_dir

# Extract multiple archives to a common output directory
try7z extract archive1.7z archive2.zip -o output_dir

# Try an additional password first
try7z extract path/to/archive.7z -p "specific_password"

# Force overwrite existing output directory without confirmation
try7z extract path/to/archive.7z -f
try7z extract path/to/archive.7z -o output_dir -f
```

### Shell Completion

```bash
# Print bash completion script to stdout
try7z autocompletion --shell bash

# Install bash completion (auto-updates ~/.bashrc)
try7z autocompletion --shell bash --install

# Install PowerShell completion (auto-updates $PROFILE)
try7z autocompletion --shell pwsh --install
```

### Using Python Module

You can also run the tool using Python's module syntax:

```bash
python -m try7z extract path/to/archive.7z
```

## Development

### Run Tests

```bash
pytest
```

### Run Benchmarks

```bash
# Run only benchmark tests (via marker)
pytest -m benchmark

# Run only benchmark tests (via file pattern)
pytest tests\benchmark_*.py --benchmark-only

# Run with verbose output and statistics table
pytest -m benchmark -v

# Run unit tests + benchmarks together
pytest --benchmark-skip=false

# Save benchmark results to JSON for comparison
pytest -m benchmark --benchmark-json=benchmark_results.json

# Compare against a saved baseline
pytest -m benchmark --benchmark-compare
```

### Linting

```bash
ruff check .
```

### Type Checking

```bash
mypy try7z/
```

### Build Documentation

```bash
python docs/build.py
```

Open `docs/_build/html/index.html` in a web browser after building.

## Project Structure

```
try7z/
├── try7z/          # Main Python package
│   ├── __init__.py
│   ├── __main__.py            # Entry point for `python -m try7z`
│   ├── main.py                # CLI entry point with argparse
│   ├── completions.py         # Shell completion generation
│   ├── password_manager.py    # Password storage and management
│   ├── extractor.py           # 7-Zip extraction logic
│   ├── utils.py               # Custom exceptions and helpers
│   └── lib/
│       └── win-x64/
│           ├── 7z.exe         # Bundled 7-Zip executable
│           ├── 7z.dll         # Bundled 7-Zip library
│           └── 7-zip.dll      # Bundled 7-Zip codec library
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared pytest fixtures
│   ├── test_cli.py
│   ├── test_password_manager.py
│   ├── test_extractor.py
│   ├── test_utils.py
│   ├── benchmark_extractor.py   # Extraction performance benchmarks
│   ├── benchmark_password_manager.py  # Password manager benchmarks
│   └── benchmark_end_to_end.py  # CLI workflow benchmarks
├── docs/
│   ├── conf.py
│   ├── index.rst
│   ├── modules.rst
│   └── build.py
├── pyproject.toml             # Package configuration
├── MANIFEST.in                # Package data includes
├── README.md
└── AGENTS.md
```

## Storage

- Passwords are stored in plain text in the platform-specific user data directory:
  - **Windows**: `%APPDATA%\try7z\passwords.json`
  - **macOS**: `~/Library/Application Support/try7z/passwords.json`
  - **Linux**: `~/.local/share/try7z/passwords.json`

## Third-Party Software

This project uses [7-Zip](https://www.7-zip.org/) for archive extraction.

- 7-Zip is licensed under the GNU LGPL license
- Source code available at: https://www.7-zip.org/download.html

## License

MIT
