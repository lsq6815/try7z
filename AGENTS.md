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
| `main` | `try7z/main.py` | 743 | CLI entry, argparse setup |
| `cmd_extract` | `try7z/main.py` | 611 | Extraction handler (multi-archive) |
| `cmd_autocompletion` | `try7z/main.py` | 680 | Shell completion handler |
| `cmd_add_password` | `try7z/main.py` | 199 | Add password(s) handler |
| `cmd_remove_password` | `try7z/main.py` | 257 | Remove by value or index |
| `cmd_list_passwords` | `try7z/main.py` | 321 | List stored passwords |
| `cmd_clear_passwords` | `try7z/main.py` | 364 | Clear all passwords |
| `cmd_show_path` | `try7z/main.py` | 410 | Show passwords file path |
| `cmd_edit_passwords` | `try7z/main.py` | 439 | Open passwords in default editor |
| `RemovalResult` | `try7z/main.py` | 70 | Removal operation result dataclass |
| `RemovalStrategy` | `try7z/main.py` | 85 | Protocol for removal strategies |
| `RemoveByValueStrategy` | `try7z/main.py` | 112 | Remove by password value |
| `RemoveByIndexStrategy` | `try7z/main.py` | 147 | Remove by 1-based index |
| `_build_password_list` | `try7z/main.py` | 488 | Build password list with priority |
| `_resolve_output_dir` | `try7z/main.py` | 506 | Resolve output directory path |
| `_handle_existing_output` | `try7z/main.py` | 531 | Prompt/force overwrite handling |
| `_extract_single` | `try7z/main.py` | 567 | Extract single archive helper |
| `Extractor` | `try7z/extractor.py` | 123 | 7-Zip wrapper, password brute-force |
| `try_extract` | `try7z/extractor.py` | 261 | Returns `(success, password)` |
| `extract_with_passwords` | `try7z/extractor.py` | 569 | Raises `PasswordNotFoundError` on failure |
| `_try_passwords` | `try7z/extractor.py` | 217 | Try each password sequentially |
| `_extract_with_password` | `try7z/extractor.py` | 375 | Single password extraction (no progress) |
| `_extract_with_progress` | `try7z/extractor.py` | 436 | tqdm progress extraction with `-bsp1` |
| `_get_archive_file_count` | `try7z/extractor.py` | 185 | File count for progress bar total |
| `get_7z_path` | `try7z/extractor.py` | 58 | Platform binary resolution |
| `get_7z_version` | `try7z/extractor.py` | 94 | Version string from 7-Zip binary |
| `PasswordManager` | `try7z/password_manager.py` | 89 | JSON read/write, auto-save |
| `PasswordStore` | `try7z/password_manager.py` | 65 | Protocol for password storage backends |
| `get_user_data_dir` | `try7z/utils.py` | 229 | `%APPDATA%/try7z` on Windows |
| `validate_archive_path` | `try7z/utils.py` | 283 | Exists + is_file check |
| `get_package_root` | `try7z/utils.py` | 265 | Package directory for bundled resources |
| `is_supported_archive` | `try7z/utils.py` | 348 | `.7z`/`.zip`/`.rar` extension check |
| `Try7zError` | `try7z/utils.py` | 43 | Base exception |
| `PasswordManagerError` | `try7z/utils.py` | 148 | Duplicate/missing password errors |
| `PasswordValidationError` | `try7z/utils.py` | 60 | Invalid password format |
| `ExtractionError` | `try7z/utils.py` | 169 | General extraction failure |
| `InvalidArchiveError` | `try7z/utils.py` | 187 | Corrupt/unsupported archive |
| `PasswordNotFoundError` | `try7z/utils.py` | 211 | No matching password in list |
| `PasswordValidator` | `try7z/utils.py` | 78 | ABC for password validation |
| `BasicPasswordValidator` | `try7z/utils.py` | 105 | Non-empty, non-whitespace, max 1000 chars |
| `generate_bash_completion` | `try7z/completions.py` | 26 | Bash completion script generator |
| `generate_pwsh_completion` | `try7z/completions.py` | 266 | pwsh completion script generator |
| `generate_powershell_completion` | `try7z/completions.py` | 282 | Windows PowerShell completion |
| `install_completion` | `try7z/completions.py` | 487 | Install completion for shell |

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
