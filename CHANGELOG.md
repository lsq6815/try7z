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
