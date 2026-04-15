# AGENTS.md

## Project Overview

This is a 7-Zip frontend application built with Python. The main functionality is to automatically attempt to extract password-protected archives using a user-saved password list.

### Core Features
- Manage user-saved passwords
- Accept user input for archive file paths
- Automatically attempt extraction with saved passwords
- Report extraction results to the user

## Tech Stack

- **Language**: Python 3.10+
- **Archive Backend**: 7-Zip (via subprocess or py7zr library)
- **Configuration Storage**: JSON or SQLite
- **CLI/GUI**: TBD (likely CLI first, optional GUI later)

## Project Structure

```
autoPassTryUnzip/
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── password_manager.py  # Password storage and management
│   ├── extractor.py         # 7-Zip extraction logic
│   └── utils.py             # Helper functions
├── tests/
│   ├── __init__.py
│   ├── test_password_manager.py
│   └── test_extractor.py
├── config/
│   └── settings.json        # Application settings
├── data/
│   └── passwords.json       # User saved passwords (or use SQLite)
├── requirements.txt
├── pyproject.toml           # Project metadata and dependencies
├── README.md
└── AGENTS.md
```

## Development Guidelines

### Code Style
- Follow PEP 8 conventions
- Use type hints for all function signatures
- Use f-strings for string formatting
- Maximum line length: 100 characters
- Use descriptive variable and function names

### Imports Order
1. Standard library
2. Third-party libraries
3. Local modules

Example:
```python
import os
import sys
from pathlib import Path

import py7zr

from src.password_manager import PasswordManager
```

### Error Handling
- Use custom exceptions for application-specific errors
- Provide meaningful error messages to users
- Log errors for debugging purposes

### Testing
- Use pytest as the testing framework
- Aim for high test coverage on core logic
- Place test files in the `tests/` directory

### Dependencies Management
- Use `requirements.txt` for production dependencies
- Use `requirements-dev.txt` for development dependencies
- Pin dependency versions for reproducibility

## Commands

### Setup
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### Run Application
```bash
python -m src.main
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
2. Add appropriate type hints
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

### Security Considerations
- Never log or expose passwords in plain text
- Store passwords securely (consider encryption at rest)
- Validate user inputs to prevent path traversal attacks
- Handle archive bombs and malicious files gracefully

## Notes

- The application requires 7-Zip to be installed on the system if using subprocess approach
- Consider using `py7zr` library for pure Python implementation as an alternative
- Support multiple archive formats: .7z, .zip, .rar (if 7-Zip is used)
