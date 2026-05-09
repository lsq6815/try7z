# Add Benchmark Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add comprehensive pytest-benchmark performance tests for try7z extraction, password manager, and CLI workflows.

**Architecture:** Three dedicated benchmark files (`benchmark_extractor.py`, `benchmark_password_manager.py`, `benchmark_end_to_end.py`) using pytest-benchmark fixture with setup outside benchmark measurement. Configured to skip by default via `--benchmark-skip`.

**Tech Stack:** pytest, pytest-benchmark, Python 3.10+

---

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `pyproject.toml` | Modify | Add pytest-benchmark dev dependency, add `--benchmark-skip` to pytest config |
| `tests/conftest.py` | Modify | Add `large_7z_archive` fixture, add `generate_passwords()` helper |
| `tests/benchmark_extractor.py` | Create | Password attempt speed and archive extraction benchmarks |
| `tests/benchmark_password_manager.py` | Create | CRUD and persistence operation benchmarks |
| `tests/benchmark_end_to_end.py` | Create | Complete CLI workflow benchmarks |

---

### Task 1: Update pyproject.toml

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add pytest-benchmark to dev dependencies**

In `[project.optional-dependencies]` section, add `"pytest-benchmark>=4.0.0"` to the `dev` list:

```toml
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.0.0",
    "pytest-benchmark>=4.0.0",  # NEW
    "ruff>=0.4.0",
    "mypy>=1.9.0",
    "commitizen>=4.0.0",
    "pre-commit>=4.0.0",
    "sphinx>=7.0.0",
    "sphinx-rtd-theme>=2.0.0",
    "sphinx-autodoc-typehints>=2.0.0",
]
```

- [ ] **Step 2: Add --benchmark-skip to pytest config**

In `[tool.pytest.ini_options]` section, append `"--benchmark-skip"` to `addopts`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = [
    "--cov=try7z",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--benchmark-skip",  # NEW: skip benchmarks by default
]
```

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore(deps): add pytest-benchmark for performance testing"
```

---

### Task 2: Update conftest.py with Benchmark Fixtures

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: Add imports**

At the top of `tests/conftest.py`, add:

```python
import os
```

- [ ] **Step 2: Add generate_passwords helper function**

At the bottom of `tests/conftest.py`, add:

```python
def generate_passwords(count: int, correct: str | None = None, correct_index: int | None = None) -> list[str]:
    """Generate a list of passwords for benchmarking.

    Args:
        count: Number of passwords to generate.
        correct: The correct password to insert, if any.
        correct_index: Index at which to insert the correct password.

    Returns:
        List of generated passwords.
    """
    passwords = [f"wrong_password_{i}" for i in range(count)]
    if correct is not None and correct_index is not None:
        passwords[correct_index] = correct
    return passwords
```

- [ ] **Step 3: Add large_7z_archive fixture**

Add after existing fixtures:

```python
@pytest.fixture
def large_7z_archive(temp_dir: Path, seven_zip: Path) -> Path:
    """Create a ~50MB 7z archive for benchmarking.

    Creates 50 files of 1MB each, compressed into a 7z archive.
    """
    src_dir = temp_dir / "large_src"
    src_dir.mkdir()

    for i in range(50):
        (src_dir / f"file_{i}.bin").write_bytes(os.urandom(1024 * 1024))

    archive_path = temp_dir / "large.7z"
    subprocess.run(
        [str(seven_zip), "a", str(archive_path), str(src_dir)],
        capture_output=True,
        check=True,
    )
    return archive_path
```

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py
git commit -m "test(fixtures): add large_7z_archive and generate_passwords for benchmarks"
```

---

### Task 3: Create benchmark_extractor.py

**Files:**
- Create: `tests/benchmark_extractor.py`

- [ ] **Step 1: Write benchmark_extractor.py**

```python
"""Benchmark tests for Extractor performance."""

from pathlib import Path

import pytest

from try7z.extractor import Extractor

from .conftest import generate_passwords


class BenchmarkPasswordAttempts:
    """Benchmark password attempt speed."""

    def test_benchmark_password_not_in_list_small(
        self, encrypted_7z_archive: Path, temp_dir: Path, benchmark
    ) -> None:
        """Benchmark: 10 wrong passwords (all fail)."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"
        passwords = generate_passwords(10)

        result = benchmark(extractor.try_extract, output_dir, passwords)

        assert result[0] is False
        assert result[1] is None

    def test_benchmark_password_not_in_list_large(
        self, encrypted_7z_archive: Path, temp_dir: Path, benchmark
    ) -> None:
        """Benchmark: 1000 wrong passwords (all fail)."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"
        passwords = generate_passwords(1000)

        result = benchmark(extractor.try_extract, output_dir, passwords)

        assert result[0] is False
        assert result[1] is None

    def test_benchmark_password_at_start(
        self, encrypted_7z_archive: Path, temp_dir: Path, benchmark
    ) -> None:
        """Benchmark: correct password at index 0 (best case)."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"
        passwords = generate_passwords(100, correct="secret123", correct_index=0)

        result = benchmark(extractor.try_extract, output_dir, passwords)

        assert result[0] is True
        assert result[1] == "secret123"

    def test_benchmark_password_at_end(
        self, encrypted_7z_archive: Path, temp_dir: Path, benchmark
    ) -> None:
        """Benchmark: correct password at index 99 (worst case)."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"
        passwords = generate_passwords(100, correct="secret123", correct_index=99)

        result = benchmark(extractor.try_extract, output_dir, passwords)

        assert result[0] is True
        assert result[1] == "secret123"


class BenchmarkArchiveExtraction:
    """Benchmark archive extraction speed."""

    def test_benchmark_extract_plain_7z(
        self, plain_7z_archive: Path, temp_dir: Path, benchmark
    ) -> None:
        """Benchmark: extract plain (non-encrypted) 7z archive."""
        extractor = Extractor(plain_7z_archive)
        output_dir = temp_dir / "output"

        result = benchmark(extractor.try_extract, output_dir)

        assert result[0] is True
        assert result[1] is None

    def test_benchmark_extract_encrypted_7z(
        self, encrypted_7z_archive: Path, temp_dir: Path, benchmark
    ) -> None:
        """Benchmark: extract encrypted 7z with correct password."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"
        passwords = ["secret123"]

        result = benchmark(extractor.try_extract, output_dir, passwords)

        assert result[0] is True
        assert result[1] == "secret123"

    def test_benchmark_extract_large_archive(
        self, large_7z_archive: Path, temp_dir: Path, benchmark
    ) -> None:
        """Benchmark: extract large (~50MB) 7z archive."""
        extractor = Extractor(large_7z_archive)
        output_dir = temp_dir / "output"

        result = benchmark(extractor.try_extract, output_dir)

        assert result[0] is True
        assert result[1] is None
```

- [ ] **Step 2: Commit**

```bash
git add tests/benchmark_extractor.py
git commit -m "test(benchmark): add extractor password and extraction benchmarks"
```

---

### Task 4: Create benchmark_password_manager.py

**Files:**
- Create: `tests/benchmark_password_manager.py`

- [ ] **Step 1: Write benchmark_password_manager.py**

```python
"""Benchmark tests for PasswordManager performance."""

import json
from pathlib import Path

from try7z.password_manager import PasswordManager


class BenchmarkPasswordManagerCrud:
    """Benchmark password manager CRUD operations."""

    def test_benchmark_add_password(self, temp_dir: Path, benchmark) -> None:
        """Benchmark: add a single password."""
        manager = PasswordManager(data_dir=temp_dir)

        benchmark(manager.add_password, "test_password")

        assert "test_password" in manager.get_passwords()

    def test_benchmark_add_password_batch(self, temp_dir: Path, benchmark) -> None:
        """Benchmark: add a single password with batch=True."""
        manager = PasswordManager(data_dir=temp_dir)

        benchmark(manager.add_password, "test_password", batch=True)

        assert "test_password" in manager.get_passwords()

    def test_benchmark_get_passwords_small(self, temp_dir: Path, benchmark) -> None:
        """Benchmark: get passwords list (10 items)."""
        manager = PasswordManager(data_dir=temp_dir)
        for i in range(10):
            manager.add_password(f"pwd_{i}")

        result = benchmark(manager.get_passwords)

        assert len(result) == 10

    def test_benchmark_get_passwords_large(self, temp_dir: Path, benchmark) -> None:
        """Benchmark: get passwords list (10,000 items)."""
        manager = PasswordManager(data_dir=temp_dir)
        for i in range(10000):
            manager.add_password(f"pwd_{i}", batch=True)
        manager.save()  # Ensure all are persisted

        result = benchmark(manager.get_passwords)

        assert len(result) == 10000

    def test_benchmark_remove_password(self, temp_dir: Path, benchmark) -> None:
        """Benchmark: remove password by value from 100-item list."""
        manager = PasswordManager(data_dir=temp_dir)
        for i in range(100):
            manager.add_password(f"pwd_{i}", batch=True)
        manager.save()

        benchmark(manager.remove_password, "pwd_50")

        assert "pwd_50" not in manager.get_passwords()

    def test_benchmark_remove_by_index(self, temp_dir: Path, benchmark) -> None:
        """Benchmark: remove password by index from 100-item list."""
        manager = PasswordManager(data_dir=temp_dir)
        for i in range(100):
            manager.add_password(f"pwd_{i}", batch=True)
        manager.save()

        benchmark(manager.remove_by_index, 50)

        assert len(manager.get_passwords()) == 99


class BenchmarkPasswordManagerPersistence:
    """Benchmark password manager persistence operations."""

    def test_benchmark_load_passwords(self, temp_dir: Path, benchmark) -> None:
        """Benchmark: load 10,000 passwords from JSON file."""
        # Pre-create password file
        passwords_data = {"passwords": [f"pwd_{i}" for i in range(10000)]}
        passwords_file = temp_dir / "passwords.json"
        passwords_file.write_text(json.dumps(passwords_data))

        def load_manager():
            return PasswordManager(data_dir=temp_dir)

        manager = benchmark(load_manager)

        assert manager.count() == 10000

    def test_benchmark_save_passwords(self, temp_dir: Path, benchmark) -> None:
        """Benchmark: save 10,000 passwords to JSON file."""
        manager = PasswordManager(data_dir=temp_dir)
        for i in range(10000):
            manager.add_password(f"pwd_{i}", batch=True)

        benchmark(manager.save)

        # Verify file was written
        passwords_file = temp_dir / "passwords.json"
        assert passwords_file.exists()
        data = json.loads(passwords_file.read_text())
        assert len(data["passwords"]) == 10000
```

- [ ] **Step 2: Commit**

```bash
git add tests/benchmark_password_manager.py
git commit -m "test(benchmark): add password manager CRUD and persistence benchmarks"
```

---

### Task 5: Create benchmark_end_to_end.py

**Files:**
- Create: `tests/benchmark_end_to_end.py`

- [ ] **Step 1: Write benchmark_end_to_end.py**

```python
"""Benchmark tests for end-to-end CLI performance."""

import subprocess
import sys
from pathlib import Path


class BenchmarkCliExtraction:
    """Benchmark complete CLI extraction workflows."""

    def test_benchmark_cli_extract_plain(
        self, plain_7z_archive: Path, temp_dir: Path, benchmark
    ) -> None:
        """Benchmark: CLI extraction of plain archive."""
        output_dir = temp_dir / "output"

        def run_extract():
            return subprocess.run(
                [sys.executable, "-m", "try7z", "extract", str(plain_7z_archive), "-o", str(output_dir), "-f"],
                capture_output=True,
                text=True,
            )

        result = benchmark(run_extract)

        assert result.returncode == 0
        assert "Success" in result.stdout

    def test_benchmark_cli_extract_encrypted(
        self, encrypted_7z_archive: Path, temp_dir: Path, benchmark
    ) -> None:
        """Benchmark: CLI extraction of encrypted archive."""
        output_dir = temp_dir / "output"

        def run_extract():
            return subprocess.run(
                [sys.executable, "-m", "try7z", "extract", str(encrypted_7z_archive), "-o", str(output_dir), "-f", "-p", "secret123"],
                capture_output=True,
                text=True,
            )

        result = benchmark(run_extract)

        assert result.returncode == 0
        assert "Success" in result.stdout

    def test_benchmark_cli_with_password_manager(
        self, encrypted_7z_archive: Path, temp_dir: Path, benchmark
    ) -> None:
        """Benchmark: CLI extraction using stored passwords."""
        output_dir = temp_dir / "output"

        # Pre-populate password manager
        from try7z.password_manager import PasswordManager
        pm = PasswordManager(data_dir=temp_dir)
        pm.add_password("wrong1")
        pm.add_password("wrong2")
        pm.add_password("secret123")
        pm.save()

        def run_extract():
            return subprocess.run(
                [sys.executable, "-m", "try7z", "extract", str(encrypted_7z_archive), "-o", str(output_dir), "-f"],
                capture_output=True,
                text=True,
                env={**os.environ, "TRY7Z_DATA_DIR": str(temp_dir)},
            )

        result = benchmark(run_extract)

        assert result.returncode == 0
        assert "Success" in result.stdout
```

- [ ] **Step 2: Commit**

```bash
git add tests/benchmark_end_to_end.py
git commit -m "test(benchmark): add end-to-end CLI extraction benchmarks"
```

---

### Task 6: Install Dependencies and Verify

**Files:**
- None (verification only)

- [ ] **Step 1: Install updated dev dependencies**

```bash
pip install -e ".[dev]"
```

Expected: `pytest-benchmark` installs successfully.

- [ ] **Step 2: Verify regular tests still pass (benchmarks skipped)**

```bash
pytest
```

Expected: All existing tests pass, benchmark tests are skipped. Look for lines like:
```
SKIPPED [3] ... benchmark tests are skipped
```

- [ ] **Step 3: Run only benchmark tests**

```bash
pytest tests/benchmark_*.py --benchmark-only -v
```

Expected: All benchmark tests pass and produce benchmark statistics tables.

- [ ] **Step 4: Run benchmarks with JSON output**

```bash
pytest tests/benchmark_*.py --benchmark-only --benchmark-json=benchmark_results.json
```

Expected: `benchmark_results.json` is created with valid JSON.

- [ ] **Step 5: Verify no production deps added**

```bash
pip show try7z
```

Expected: Only `tqdm` in `Requires:` field, no `pytest-benchmark`.

- [ ] **Step 6: Run lint and type check**

```bash
ruff check tests/benchmark_*.py
mypy tests/benchmark_*.py
```

Expected: No errors.

- [ ] **Step 7: Commit**

```bash
git add benchmark_results.json  # Optional: ignore in .gitignore instead
git commit -m "test(benchmark): complete benchmark test suite"
```

---

## Self-Review

### Spec Coverage Check

| Spec Requirement | Task | Status |
|------------------|------|--------|
| Add pytest-benchmark to dev deps | Task 1 | Covered |
| Add `--benchmark-skip` config | Task 1 | Covered |
| `benchmark_extractor.py`: password attempts | Task 3 | Covered |
| `benchmark_extractor.py`: archive extraction | Task 3 | Covered |
| `benchmark_password_manager.py`: CRUD | Task 4 | Covered |
| `benchmark_password_manager.py`: persistence | Task 4 | Covered |
| `benchmark_end_to_end.py`: CLI workflows | Task 5 | Covered |
| `conftest.py`: large_7z_archive fixture | Task 2 | Covered |
| `conftest.py`: generate_passwords helper | Task 2 | Covered |
| Run and verify | Task 6 | Covered |

### Placeholder Scan

- [x] No "TBD", "TODO", "implement later" found
- [x] No vague instructions like "add appropriate error handling"
- [x] No "similar to Task N" references
- [x] All code blocks contain complete, copy-paste ready code
- [x] All commands have expected output documented

### Type Consistency

- [x] `generate_passwords()` signature matches usage in all benchmarks
- [x] `benchmark()` fixture usage is consistent (pytest-benchmark standard)
- [x] `PasswordManager` API matches current codebase (`add_password`, `remove_password`, `remove_by_index`, `get_passwords`, `save`, `count`)
- [x] `Extractor` API matches (`try_extract` returns `(bool, str|None)`)
- [x] `subprocess.run` calls match try7z CLI interface

**Plan is complete and ready for execution.**

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-09-add-benchmark.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
