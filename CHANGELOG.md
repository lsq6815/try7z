## v1.2.0 (2026-05-24)

### Feat

- add -F/--flatten CLI flag for smart extraction
- add _flatten_extract helper and flatten parameter to extraction methods
- add _flatten_and_move function with tests
- add _compute_skip_depth function with tests

### Fix

- use getattr for flatten to avoid AttributeError in tests
- remove dead code and update docstring for flatten parameter
- handle edge cases in _flatten_and_move

## v1.1.0 (2026-05-21)

### Feat

- add python -m docs entry point
- **mypy**: expand type checking to docs and tests directories
- integrate directory scanning into extract command
- add _resolve_input_paths function for directory scanning

### Fix

- update try7z.main references to try7z.cli.main

### Refactor

- reorganize CLI code into try7z/cli package
- **cli**: move test_cli.py to tests/cli/ and fix entry point
- move main.py to try7z/cli/ and update imports
- move completions.py to try7z/cli/

## v1.0.1 (2026-05-10)

### Fix

- **lint**: escape backslash in regex pattern to avoid invalid escape sequence
- **completions**: handle spaces in filenames and prevent duplicate installs

## v1.0.0 (2026-05-09)

### BREAKING CHANGE

- None

### Feat

- **config**: add pytest benchmark markers and update docs with marker-based commands
- **password_manager**: add batch mode with deferred writes

### Fix

- **benchmark**: add missing pytest markers and test discovery config

### Refactor

- extract password attempt loop and fix code quality issues
- apply strategy pattern to cmd_remove_password()
- decouple CLI commands and extract helper functions

## v0.6.0 (2026-05-08)

### Feat

- add PasswordValidationError handling to CLI
- integrate PasswordValidator into PasswordManager.add_password()
- add whitespace and max length validation to BasicPasswordValidator
- add PasswordValidator ABC and BasicPasswordValidator with empty check
- improve user experience from optimization report
- **extract**: support multiple archive arguments

### Fix

- update exception hierarchy in module docstring

### Refactor

- apply modern Python practices from optimization report

## v0.5.1 (2026-05-05)

### Refactor

- read version dynamically from package metadata

## v0.5.0 (2026-05-05)

### BREAKING CHANGE

- AutoPassError no longer exists. Update all try/except
blocks and imports to use Try7zError instead.
- Package and CLI command renamed. Users must update
their commands from autopass-unzip to try7z.

### Feat

- add shell autocompletion for bash and PowerShell
- add build date to -v output
- add pure Python docs build script (docs/build.py)
- rename project to try7z and bump version to 0.5.0
- add output directory overwrite confirmation
- show password attempt progress and found count
- add progress bar support for archive extraction
- add --version flag

### Fix

- replace deprecated datetime.utcnow() with timezone-aware alternative
- distinguish pwsh from powershell in autocompletion install
- prevent silent data loss on corrupt passwords file (CRITICAL-2)
- clean up empty output directory when extraction fails
- handle --version line breaks on Windows

### Refactor

- rename AutoPassError to Try7zError
