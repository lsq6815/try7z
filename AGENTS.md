# try7z — Agent Notes

Python 3.10+ CLI frontend for 7-Zip. Manages a password list and auto-extracts password-protected `.7z`/`.zip`/`.rar` archives using a bundled 7-Zip executable.

## Where to Look

| Task | File | Notes |
|------|------|-------|
| Add CLI command | `try7z/main.py` | Add subparser + handler function |
| Modify extraction | `try7z/extractor.py` | `Extractor` class, `_extract_with_password` |
| Change passwords | `try7z/password_manager.py` | `PasswordManager` class |
| Add exception | `try7z/utils.py` | Inherit from `Try7zError` |
| Add tests | `tests/test_*.py` | Mirror module under test |
| Build docs | `docs/build.py` | Outputs to `docs/_build/html/` |

## Code Map

| Symbol | File | Line | Role |
|--------|------|------|------|
| `main` | `try7z/main.py` | 560 | CLI entry, argparse setup |
| `cmd_extract` | `try7z/main.py` | 390 | Extraction handler |
| `cmd_autocompletion` | `try7z/main.py` | 497 | Shell completion handler |
| `Extractor` | `try7z/extractor.py` | 120 | 7-Zip wrapper, password brute-force |
| `try_extract` | `try7z/extractor.py` | 214 | Returns `(success, password)` |
| `_get_archive_file_count` | `try7z/extractor.py` | 182 | File count for progress bar |
| `_extract_with_progress` | `try7z/extractor.py` | 419 | tqdm progress extraction |
| `extract_with_passwords` | `try7z/extractor.py` | 554 | Raises `PasswordNotFoundError` |
| `PasswordManager` | `try7z/password_manager.py` | 58 | JSON read/write |
| `get_7z_path` | `try7z/extractor.py` | 55 | Platform binary resolution |
| `get_7z_version` | `try7z/extractor.py` | 91 | Version string |
| `get_user_data_dir` | `try7z/utils.py` | 139 | `%APPDATA%/try7z` on Windows |
| `validate_archive_path` | `try7z/utils.py` | 193 | Exists + is_file check |

## Commands

```bash
# Setup
pip install -e ".[dev]"
pre-commit install   # required to enforce commit-msg hooks

# Test (pytest.ini auto-enables coverage + HTML report)
pytest

# Verify
ruff check .
mypy try7z/

# Standard build
python -m build

# Full build after updating bundled 7z.exe/DLLs (setuptools caches build/lib/)
rm -r build dist *.egg-info
pip install . --no-cache-dir --force-reinstall

# Docs
python docs/build.py
# Open docs/_build/html/index.html

# Release (maintainers)
cz bump --dry-run
cz bump
git push --follow-tags origin master
```

## Conventions

- **Type hints**: `X \| None` syntax (PEP 604), mypy strict mode.
- **Line length**: 100 (ruff).
- **Imports**: stdlib → third-party → local.
- **Docstrings**: Google-style, with `>>>` doctests in public APIs.
- **Password indices**: 1-based in CLI, 0-based internally.
- **Commits**: Conventional Commits enforced by pre-commit hooks. Use imperative mood (`add`, `fix`, not `added`, `fixed`). Breaking changes require `!` prefix **and** `BREAKING CHANGE:` footer.
- **No runtime deps**: production only has `tqdm`. Do not add dependencies.

## Critical Gotchas

- **Do NOT** suppress type errors with `# type: ignore` or `Any`.
- **Do NOT** add runtime dependencies — keep production deps at zero.
- **Do NOT** encrypt passwords — intentional plain-text JSON for user editing.
- **Do NOT** forget full clean-build after updating `7z.exe` or DLLs in `try7z/lib/win-x64/`.
- **Windows x64 only** at runtime; Linux/macOS paths exist in `get_7z_path()` but require manual binary placement.
- **Two-phase extraction**: when progress is enabled, `Extractor` first finds the password silently, then runs again with `tqdm` (`-bsp1` flag).
- **Raw byte parsing**: `_extract_with_progress` reads stdout byte-by-byte to handle `\r` carriage returns from 7-Zip.
- **Corrupt JSON recovery**: `PasswordManager` backs up corrupt `passwords.json` to `.json.bak` before resetting.
- **Version drift**: `cz bump` only updates `pyproject.toml`; `try7z/__init__.py::__version__` must be updated manually (or add the file to `tool.commitizen.version_files`).
