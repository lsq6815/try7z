# AutoPassTryUnzip

A 7-Zip frontend application for automatically extracting password-protected archives using a user-saved password list.

## Features

- Manage password list (add, remove, list, clear)
- Automatically try multiple passwords for archive extraction
- Support for `.7z`, `.zip`, `.rar` formats
- Bundled 7-Zip executable - no external dependencies

## Installation

### From Source

```bash
# Clone the repository
git clone <repository-url>
cd autoPassTryUnzip

# Create virtual environment (recommended)
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS

# Install the package
pip install .
```

### Development Installation

```bash
pip install -e .
pip install -r requirements-dev.txt
```

## Usage

After installation, use the `autopass-unzip` command:

### Password Management

```bash
# Show version information
autopass-unzip -v

# Add password(s)
autopass-unzip add "my_password"
autopass-unzip add "pwd1" "pwd2" "pwd3"  # Add multiple at once

# List stored passwords (shows 1-based index)
autopass-unzip list

# Remove password(s) by value
autopass-unzip remove "my_password"
autopass-unzip remove "pwd1" "pwd2" "pwd3"  # Remove multiple at once

# Remove password(s) by index (from 'list' command)
autopass-unzip remove -i 3          # Remove index 3
autopass-unzip remove -i 1 5 10     # Remove multiple indices

# Show passwords file path
autopass-unzip path

# Open passwords file in default editor
autopass-unzip edit

# Clear all passwords (with confirmation)
autopass-unzip clear

# Clear all passwords (skip confirmation)
autopass-unzip clear -f
```

### Archive Extraction

```bash
# Extract an archive using stored passwords
autopass-unzip extract path/to/archive.7z

# Extract with custom output directory
autopass-unzip extract path/to/archive.7z -o output_dir

# Try an additional password first
autopass-unzip extract path/to/archive.7z -p "specific_password"
```

### Using Python Module

You can also run the tool using Python's module syntax:

```bash
python -m autopasstryunzip extract path/to/archive.7z
```

## Development

### Run Tests

```bash
pytest
```

### Linting

```bash
ruff check .
```

### Type Checking

```bash
mypy autopasstryunzip/
```

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
├── pyproject.toml             # Package configuration
├── MANIFEST.in                # Package data includes
├── requirements.txt
├── requirements-dev.txt
├── README.md
└── AGENTS.md
```

## Storage

- Passwords are stored in plain text in the platform-specific user data directory:
  - **Windows**: `%APPDATA%\autoPassTryUnzip\passwords.json`
  - **macOS**: `~/Library/Application Support/autoPassTryUnzip/passwords.json`
  - **Linux**: `~/.local/share/autoPassTryUnzip/passwords.json`

## Third-Party Software

This project uses [7-Zip](https://www.7-zip.org/) for archive extraction.

- 7-Zip is licensed under the GNU LGPL license
- Source code available at: https://www.7-zip.org/download.html

## License

MIT
