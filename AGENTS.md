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
- **Archive Backend**: py7zr library (7z format only)
- **Password Storage**: JSON file (plain text)
- **Interface**: CLI

## Project Structure

```
autoPassTryUnzip/
├── src/
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── password_manager.py  # Password storage and management
│   ├── extractor.py         # 7-Zip extraction logic
│   └── utils.py             # Custom exceptions and helpers
├── tests/
│   ├── __init__.py
│   ├── test_password_manager.py
│   └── test_extractor.py
├── config/
│   └── settings.json
├── data/
│   └── passwords.json       # User saved passwords
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
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
import json
from pathlib import Path

import py7zr

from src.utils import PasswordManagerError
```

### Error Handling
- Use custom exceptions from `src.utils`:
  - `AutoPassError` - base exception
  - `PasswordManagerError` - password management errors
  - `ExtractionError` - extraction errors
  - `InvalidArchiveError` - invalid archive errors
  - `PasswordNotFoundError` - no matching password
- Provide meaningful error messages to users

### Testing
- Use pytest as the testing framework
- Place test files in the `tests/` directory
- Use `tempfile.TemporaryDirectory` for test fixtures

### Dependencies
- Production: `py7zr>=0.21.0`
- Development: `pytest`, `ruff`, `mypy`

## Commands

### Run Application
```bash
python -m src.main <command> [options]

# Commands:
#   add <password>     Add a password
#   remove <password>  Remove a password
#   list               List stored passwords
#   clear [-f]         Clear all passwords
#   extract <archive>  Extract an archive
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
mypy src/
```

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

- Only `.7z` format is fully supported via py7zr library
- Passwords are stored in plain text in `data/passwords.json`
- The `data/passwords.json` file is excluded from git via `.gitignore`
