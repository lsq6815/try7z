# Contributing to try7z

Thank you for your interest in contributing to try7z! This project follows the **Conventional Commits** specification to maintain a clear and structured commit history.

## Conventional Commits Specification

Every commit message must follow this format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Required Elements

1. **`<type>`** — A mandatory noun prefix describing the nature of the change.
2. **`<description>`** — A short summary of the change in the imperative mood (e.g., "add", "fix", "refactor").

### Optional Elements

- **`[scope]`** — A noun in parentheses describing the affected area (e.g., `cli`, `extractor`, `password-manager`).
- **`[body]`** — A longer explanation of the change, separated from the description by a blank line.
- **`[footer(s)]`** — Metadata such as references, breaking change descriptions, etc.

## Commit Types

This project uses the following commit types:

| Type | Description | SemVer Impact |
|------|-------------|---------------|
| `feat` | Introduces a new feature or capability | `MINOR` |
| `fix` | Fixes a bug or incorrect behavior | `PATCH` |
| `docs` | Updates documentation, README, AGENTS.md, or code comments | None |
| `test` | Adds, updates, or fixes tests | None |
| `refactor` | Restructures code without changing external behavior | None |
| `style` | Code formatting changes (whitespace, semicolons, quotes, etc.) | None |
| `perf` | Improves performance or reduces resource usage | None |
| `chore` | Changes to build process, tooling, dependencies, or auxiliary tasks | None |
| `build` | Changes affecting the build system or packaging (e.g., pyproject.toml, setuptools) | None |

## BREAKING CHANGE Convention

A **breaking change** is any modification that requires users to update their code, configuration, or workflow to maintain compatibility.

### Marking Breaking Changes

Every breaking change **MUST** be marked with both:

1. **`!` after the type/scope** — Provides an immediate visual signal.
2. **`BREAKING CHANGE:` footer** — Provides a detailed explanation of the impact and migration path.

```
<type>[optional scope]!: <description>

[optional body]

BREAKING CHANGE: <detailed description of what changed and how to migrate>
```

### BREAKING CHANGE Examples

**Correct — Both markers present:**

```
feat(cli)!: rename --output-dir to --dest

The short flag `-o` remains unchanged. Update scripts using
`--output-dir` to use `--dest` instead.

BREAKING CHANGE: `--output-dir` flag is removed. Use `--dest`.
```

```
refactor!: rename AutoPassError to Try7zError

All exception classes now use the `Try7zError` base class.

BREAKING CHANGE: `AutoPassError` is renamed to `Try7zError`.
Migrate by replacing all `AutoPassError` imports/catches with `Try7zError`.
```

**Incorrect — Missing `!` marker:**

```
feat: change default extraction behavior

BREAKING CHANGE: extraction now skips existing files by default.
```

**Incorrect — Missing `BREAKING CHANGE:` footer:**

```
feat(cli)!: remove --legacy flag

This flag has been deprecated for three releases.
```

### When to Use BREAKING CHANGE

Use the breaking change notation when:

- Removing or renaming CLI flags, commands, or arguments
- Changing default behavior that affects user workflows
- Renaming public APIs, classes, or functions
- Modifying configuration file formats or locations
- Updating minimum supported Python versions
- Changing exit codes or output formats that scripts may depend on

## Scope Guidelines

Use a scope to clarify which part of the project is affected. Common scopes for this project:

| Scope | Area |
|-------|------|
| `cli` | Command-line interface, argument parsing |
| `extractor` | Archive extraction logic |
| `password-manager` | Password list storage and management |
| `utils` | Utility functions and helpers |
| `docs` | Documentation generation and content |
| `tests` | Test suite |
| `build` | Build system, packaging, CI/CD |
| *(none)* | Cross-cutting or project-wide changes |

## SemVer Mapping

| Commit Type | Version Bump |
|-------------|--------------|
| `fix` | `PATCH` (0.0.1) |
| `feat` | `MINOR` (0.1.0) |
| Any type with `BREAKING CHANGE` | `MAJOR` (1.0.0) |
| Other types | No version bump |

## Commit Message Examples

### Feature Addition

```
feat(extractor): add progress bar for large archives

Displays a tqdm progress bar when extracting archives over 100MB.
Respects the --quiet flag to suppress output.
```

### Bug Fix

```
fix(password-manager): prevent crash on empty password file

Return an empty list instead of raising JSONDecodeError when
the passwords file contains only whitespace.
```

### Documentation

```
docs: update README with Windows installation steps

Add PowerShell execution policy note and pip install command.
```

### Test

```
test(extractor): add coverage for password brute-force timeout

Mock the subprocess to simulate timeout and verify graceful
degradation with appropriate error message.
```

### Refactor

```
refactor(utils): consolidate path validation helpers

Merge validate_archive_path and validate_output_dir into a
single validate_path function with mode parameter.
```

### Style

```
style: reformat extractor.py with ruff

No functional changes. Apply consistent import ordering and
line wrapping.
```

### Chore

```
chore: bump minimum tqdm version to 4.70.0

Required for the new close() behavior fix on Windows.
```

## Writing Good Commit Messages

- **Use the imperative mood** in the description: "add feature" not "added feature"
- **Keep the first line under 72 characters** when possible
- **Reference issues** in the footer when applicable: `Fixes: #123`
- **Separate subject from body** with a blank line
- **Explain the "why"** in the body, not just the "what"
- **One logical change per commit** — if you have multiple changes, make multiple commits

## Pull Request Process

1. Ensure all commits in your PR follow the Conventional Commits format
2. Update relevant documentation (README, AGENTS.md) if your change affects usage
3. Add or update tests for any code changes
4. Run the test suite: `pytest`
5. Run linting: `ruff check .`
6. Run type checking: `mypy try7z/`

## Releasing (Maintainers Only)

This project uses [commitizen](https://commitizen-tools.github.io/commitizen/) to automate version bumping, changelog generation, and tag creation.

### Prerequisites

```bash
pip install -e ".[dev]"
```

### Release Workflow

```bash
# 1. Preview what the next version will be
cz bump --dry-run

# 2. Bump version (updates pyproject.toml, appends to CHANGELOG.md, creates annotated tag)
cz bump

# 3. Push the new tag
git push --follow-tags origin master
```

### SemVer Mapping

| Commit Type / Marker | Version Bump | Example |
|---------------------|--------------|---------|
| `fix` | `PATCH` (0.5.1) | Bug fix release |
| `feat` | `MINOR` (0.6.0) | New feature release |
| `BREAKING CHANGE` | `MAJOR` (1.0.0) | Breaking change release |
| Other types | No bump | Docs, tests, style, etc. |

### Commit Message Hook

A `commit-msg` hook is installed via [pre-commit](https://pre-commit.com/). It validates that every commit message follows the Conventional Commits format before the commit is created.

If the hook rejects your message, amend it:

```bash
git commit --amend
```

To bypass the hook in emergencies (not recommended):

```bash
git commit --no-verify -m "..."
```

## Questions?

If you're unsure about the correct type or scope for your change, open an issue to discuss before submitting your PR.
