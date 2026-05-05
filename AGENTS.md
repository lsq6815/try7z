# PROJECT KNOWLEDGE BASE

**Generated:** 2026-04-28
**Commit:** d541eb7
**Branch:** master

## OVERVIEW

Python 3.10+ CLI frontend for 7-Zip. Manages a password list and auto-extracts password-protected `.7z`/`.zip`/`.rar` archives using a bundled 7-Zip executable.

## STRUCTURE

```
try7z/
├── try7z/              # Main package
│   ├── main.py         # CLI entry (argparse), all command handlers
│   ├── completions.py  # Shell completion generation and installation
│   ├── extractor.py    # Archive extraction via bundled 7z.exe
│   ├── password_manager.py  # JSON password storage
│   ├── utils.py        # Exceptions, path helpers, archive validation
│   └── lib/win-x64/    # Bundled binaries (Windows x64)
│       ├── 7z.exe
│       ├── 7z.dll
│       └── 7-zip.dll
├── tests/              # pytest suite
│   ├── test_cli.py
│   ├── test_extractor.py
│   ├── test_password_manager.py
│   └── test_utils.py
├── docs/               # Sphinx docs (RTD theme)
│   ├── conf.py
│   ├── index.rst
│   ├── modules.rst
│   └── build.py        # Pure-Python build script
└── pyproject.toml      # setuptools config, ruff/mypy/pytest settings, dependencies
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add CLI command | `try7z/main.py` | Add subparser + handler function |
| Add shell completion | `try7z/completions.py` | Completion script generation/install |
| Modify extraction logic | `try7z/extractor.py` | `Extractor` class, `_extract_with_password` |
| Change password storage | `try7z/password_manager.py` | `PasswordManager` class |
| Add exception type | `try7z/utils.py` | Inherit from `Try7zError` |
| Add tests | `tests/test_*.py` | Mirror module under test |
| Build docs | `docs/build.py` | Outputs to `docs/_build/html/` |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `main` | function | `try7z/main.py:560` | CLI entry point, argparse setup |
| `cmd_extract` | function | `try7z/main.py:390` | Archive extraction handler |
| `cmd_autocompletion` | function | `try7z/main.py:497` | Shell completion handler |
| `Extractor` | class | `try7z/extractor.py:120` | 7-Zip wrapper, password brute-force |
| `try_extract` | method | `try7z/extractor.py:214` | Returns `(success, password)` |
| `_get_archive_file_count` | method | `try7z/extractor.py:182` | Internal file count for progress bar |
| `_extract_with_progress` | method | `try7z/extractor.py:419` | Internal tqdm progress extraction |
| `extract_with_passwords` | method | `try7z/extractor.py:554` | Raises `PasswordNotFoundError` on failure |
| `PasswordManager` | class | `try7z/password_manager.py:58` | JSON read/write |
| `get_7z_path` | function | `try7z/extractor.py:55` | Platform-specific binary resolution |
| `get_7z_version` | function | `try7z/extractor.py:91` | Returns 7-Zip version string |
| `get_user_data_dir` | function | `try7z/utils.py:139` | `%APPDATA%/try7z` on Windows |
| `validate_archive_path` | function | `try7z/utils.py:193` | Exists + is_file check |

## CONVENTIONS

- **Type hints**: `X \| None` syntax (PEP 604), enforced by mypy strict mode
- **Line length**: 100 (ruff `line-length`)
- **Import order**: stdlib → third-party → local modules
- **Docstrings**: Google-style, with `>>>` doctests in public APIs
- **Password indices**: 1-based in CLI, 0-based internally
- **Progress bars**: `tqdm` for extraction progress (`-bsp1` 7-Zip flag)
- **Commit messages**: Follow Conventional Commits (see CONTRIBUTING.md); format is `<type>[optional scope]: <description>` in imperative mood

## ANTI-PATTERNS (THIS PROJECT)

- **Do NOT** suppress type errors with `# type: ignore` or `Any` — mypy is strict
- **Do NOT** use `as any` / `@ts-ignore` — this is Python, but same rule applies
- **Do NOT** add runtime dependencies — production has zero deps (only `tqdm` currently)
- **Do NOT** store passwords encrypted — intentional plain-text JSON for user editing
- **Do NOT** forget full build after updating `7z.exe` — setuptools caches in `build/`
- **Do NOT** commit with non-Conventional Commits format — e.g., `Update file` or `Fix bug` without type prefix
- **Do NOT** use `BREAKING CHANGE` without `!` marker in the type prefix — both markers must be present
- **Do NOT** omit `BREAKING CHANGE:` footer when introducing breaking changes — footer is required even with `!` marker
- **Do NOT** use past tense in commit descriptions — use imperative mood (`add`, `fix`, not `added`, `fixed`)

## UNIQUE STYLES

- **Bundled binary**: 7-Zip executable ships inside the Python package (`lib/win-x64/`)
- **Two-phase extraction**: When progress enabled, first pass finds password silently, second pass shows `tqdm` bar
- **Raw byte parsing**: `_extract_with_progress` reads stdout byte-by-byte to handle `\r` carriage returns from 7-Zip
- **Corrupt file recovery**: `PasswordManager` backs up corrupt `passwords.json` to `.json.bak` before resetting

## COMMANDS

```bash
# Development
python -m try7z <command> [options]

# Install development dependencies
pip install -e ".[dev]"

# Tests (auto-enables coverage, outputs terminal summary + HTML report)
pytest

# View HTML coverage report
# Open htmlcov/index.html

# Lint + Type check
ruff check .
mypy try7z/

# Standard build
python -m build

# Full build (after updating bundled binaries)
rm -r build dist *.egg-info
pip install . --no-cache-dir --force-reinstall

# Documentation
python docs/build.py
# Open docs/_build/html/index.html
```

## NOTES

- Windows x64 only at runtime; Linux/macOS paths exist in `get_7z_path()` but require manual binary placement
- `setuptools` caches `build/lib/` — always clean-build when updating `7z.exe`
- 7-Zip is LGPL-licensed; see README.md for attribution
- Password file location: `%APPDATA%\try7z\passwords.json` (Windows)
