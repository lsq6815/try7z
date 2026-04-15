# AutoPassTryUnzip

A 7-Zip frontend application for automatically extracting password-protected archives using a user-saved password list.

## Features

- Manage password list (add, remove, list, clear)
- Automatically try multiple passwords for archive extraction
- Support for `.7z`, `.zip`, `.rar` formats
- Bundled 7-Zip executable - no external dependencies

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd autoPassTryUnzip

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

## Usage

### Password Management

```bash
# Add a password
python -m src.main add "my_password"

# List stored passwords
python -m src.main list

# Remove a password
python -m src.main remove "my_password"

# Clear all passwords (with confirmation)
python -m src.main clear

# Clear all passwords (skip confirmation)
python -m src.main clear -f
```

### Archive Extraction

```bash
# Extract an archive using stored passwords
python -m src.main extract path/to/archive.7z

# Extract with custom output directory
python -m src.main extract path/to/archive.7z -o output_dir

# Try an additional password first
python -m src.main extract path/to/archive.7z -p "specific_password"
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
mypy src/
```

## Project Structure

```
autoPassTryUnzip/
├── lib/
│   └── win-x64/
│       └── 7z.exe            # Bundled 7-Zip executable
├── src/
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── password_manager.py  # Password storage and management
│   ├── extractor.py         # Archive extraction logic
│   └── utils.py             # Custom exceptions and helpers
├── tests/
│   ├── test_password_manager.py
│   └── test_extractor.py
├── config/
│   └── settings.json
├── data/
│   └── passwords.json       # Password storage
└── pyproject.toml
```

## Storage

- Passwords are stored in plain text in `data/passwords.json`
- The passwords file is excluded from git via `.gitignore`

## Third-Party Software

This project uses [7-Zip](https://www.7-zip.org/) for archive extraction.

- 7-Zip is licensed under the GNU LGPL license
- Source code available at: https://www.7-zip.org/download.html

## License

MIT
