# Benchmark Tests Design for try7z

**Date**: 2026-05-09  
**Author**: opencode  
**Status**: Approved  

---

## 1. Overview

This document describes the design for adding comprehensive performance benchmark tests to the try7z project using `pytest-benchmark`. The benchmarks will measure performance across three dimensions: password attempt speed, archive extraction speed, password manager operations, and end-to-end CLI workflows.

## 2. Motivation

The try7z project has undergone significant refactoring recently (strategy pattern for password removal, batch mode, decoupled CLI commands). Adding benchmarks will:

- Establish baseline performance metrics for current implementation
- Enable detection of performance regressions in future changes
- Provide data for optimizing hot paths (password brute-force loop, file I/O)
- Document expected performance characteristics for users

## 3. Design Decisions

### 3.1 Tool Choice: pytest-benchmark

**Decision**: Use `pytest-benchmark` as the benchmark framework.

**Rationale**:
- Seamless integration with existing pytest infrastructure (fixtures, conftest.py, parametrization)
- Automatic warmup and statistical aggregation (mean, median, stddev, IQR)
- Built-in history comparison (`--benchmark-compare`)
- JSON/HTML report generation for CI/CD
- Professional-grade output suitable for regression detection
- Dev-only dependency, preserving zero production runtime dependencies

**Rejected Alternatives**:
- Custom `time.perf_counter()` scripts: Too much boilerplate, no statistical rigor
- `timeit` module: Better for micro-benchmarks, awkward for integration-style tests
- Pure `pytest` with manual timing: No warmup, no statistics, fragile

### 3.2 File Organization

Benchmarks are isolated in dedicated files prefixed with `benchmark_` to:
- Separate performance concerns from functional correctness
- Allow selective execution (`pytest tests/benchmark_*.py` or `--benchmark-only`)
- Keep functional tests fast by excluding benchmarks by default

```
tests/
├── conftest.py                    # Existing shared fixtures
├── test_extractor.py              # Existing functional tests
├── test_password_manager.py       # Existing functional tests
├── test_cli.py                    # Existing functional tests
├── benchmark_extractor.py         # NEW: Extraction performance
├── benchmark_password_manager.py  # NEW: Password manager performance
└── benchmark_end_to_end.py        # NEW: CLI workflow performance
```

### 3.3 Measurement Strategy

Each benchmark follows the pattern:

```python
def test_benchmark_something(existing_fixtures, benchmark):
    # Setup (NOT measured)
    extractor = Extractor(archive_path)
    output_dir = temp_dir / "output"
    
    # Benchmark (measured)
    result = benchmark(extractor.try_extract, output_dir, passwords)
    
    # Assertions on result (NOT measured, but validated)
    assert result[0] is True
```

**Key Principles**:
1. **Setup outside benchmark**: Object initialization, temp directory creation, archive generation
2. **Single operation per benchmark**: One function call to isolate variables
3. **Validate results**: Assertions ensure the operation succeeded, not just completed quickly
4. **Use existing fixtures**: Reuse `temp_dir`, `encrypted_7z_archive`, `seven_zip` from `conftest.py`

### 3.4 Configuration

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    # ... existing deps ...
    "pytest-benchmark>=4.0.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = [
    # ... existing opts ...
    "--benchmark-skip",  # Skip benchmarks by default in regular test runs
]
```

Rationale for `--benchmark-skip`:
- Regular `pytest` runs remain fast (benchmarks can take minutes)
- CI/CD can opt-in with `--benchmark-only` or explicit benchmark file paths
- Developers can run benchmarks on-demand without modifying config

## 4. Benchmark Specifications

### 4.1 `tests/benchmark_extractor.py`

Measures archive extraction and password attempt performance.

**Class: `BenchmarkPasswordAttempts`**

| Test Name | Description | Password List Size | Expected Metric |
|-----------|-------------|-------------------|-----------------|
| `test_benchmark_password_not_in_list_small` | All passwords fail, small list | 10 | Mean time for rejection |
| `test_benchmark_password_not_in_list_large` | All passwords fail, large list | 1,000 | Scalability of rejection |
| `test_benchmark_password_at_start` | Correct password at index 0 | 100 | Best-case success time |
| `test_benchmark_password_at_end` | Correct password at index 99 | 100 | Worst-case success time |

**Class: `BenchmarkArchiveExtraction`**

| Test Name | Description | Archive Size | Notes |
|-----------|-------------|-------------|-------|
| `test_benchmark_extract_plain_7z` | Plain 7z extraction | Small (~1 file) | Baseline I/O |
| `test_benchmark_extract_encrypted_7z` | Encrypted 7z extraction | Small | Includes crypto overhead |
| `test_benchmark_extract_large_archive` | Large archive extraction | ~50MB | Requires new fixture |

**New Fixtures Needed**:
- `large_7z_archive`: Creates a ~50MB archive with multiple files. Creation time excluded from benchmark.

### 4.2 `tests/benchmark_password_manager.py`

Measures password manager CRUD and persistence operations.

**Class: `BenchmarkPasswordManagerCrud`**

| Test Name | Description | Password Count | Notes |
|-----------|-------------|---------------|-------|
| `test_benchmark_add_password` | Add single password | 1 | Basic write |
| `test_benchmark_add_password_batch` | Add with batch mode | 1 | Uses `batch=True` |
| `test_benchmark_get_passwords_small` | Retrieve list | 10 | Small dataset |
| `test_benchmark_get_passwords_large` | Retrieve list | 10,000 | Large dataset |
| `test_benchmark_remove_password` | Remove by value | 100 list | Search + remove |
| `test_benchmark_remove_by_index` | Remove by index | 100 list | Direct access |

**Class: `BenchmarkPasswordManagerPersistence`**

| Test Name | Description | Password Count | Notes |
|-----------|-------------|---------------|-------|
| `test_benchmark_load_passwords` | Load from JSON | 10,000 | File I/O + parsing |
| `test_benchmark_save_passwords` | Save to JSON | 10,000 | Serialization + write |
| `test_benchmark_load_corrupt_recovery` | Load with corrupt JSON | N/A | Tests recovery path |

**Setup Strategy**:
- Pre-populate manager with N passwords in setup phase (not measured)
- For persistence tests, create file on disk before benchmark

### 4.3 `tests/benchmark_end_to_end.py`

Measures complete user workflows via CLI subprocess.

**Class: `BenchmarkCliExtraction`**

| Test Name | Description | Command | Notes |
|-----------|-------------|---------|-------|
| `test_benchmark_cli_extract_plain` | Extract plain archive | `try7z extract plain.7z` | Full process |
| `test_benchmark_cli_extract_encrypted` | Extract with password | `try7z extract encrypted.7z` | Includes password search |
| `test_benchmark_cli_with_password_manager` | Use stored passwords | `try7z extract -p` | Password manager integration |

**Execution Strategy**:
- Use `subprocess.run([sys.executable, "-m", "try7z", ...])` for true process overhead
- Pre-create archives and password store in setup
- Measure full wall-clock time from subprocess invocation to completion

## 5. Implementation Considerations

### 5.1 Large Archive Fixture

```python
@pytest.fixture
def large_7z_archive(temp_dir: Path, seven_zip: Path) -> Path:
    """Create a ~50MB 7z archive for benchmarking."""
    src_dir = temp_dir / "large_src"
    src_dir.mkdir()
    
    # Generate multiple files totaling ~50MB
    for i in range(50):
        (src_dir / f"file_{i}.bin").write_bytes(
            os.urandom(1024 * 1024)  # 1MB each
        )
    
    archive_path = temp_dir / "large.7z"
    subprocess.run(
        [str(seven_zip), "a", str(archive_path), str(src_dir)],
        capture_output=True,
        check=True,
    )
    return archive_path
```

**Note**: This fixture creation time is excluded from benchmarks. The fixture is created once per test session (or function, depending on scope).

### 5.2 Password List Generation

For benchmarks requiring large password lists:

```python
def generate_passwords(count: int, correct: str | None = None, correct_index: int | None = None) -> list[str]:
    """Generate a list of passwords for benchmarking."""
    passwords = [f"wrong_password_{i}" for i in range(count)]
    if correct is not None and correct_index is not None:
        passwords[correct_index] = correct
    return passwords
```

### 5.3 Benchmark Parameters

Default `pytest-benchmark` settings (can be overridden per-test):
- `warmup`: True (1 round)
- `min_rounds`: 5
- `max_time`: 60 seconds per test
- `timer`: `time.perf_counter`

For very slow operations (e.g., large archive extraction), reduce `min_rounds` to 3 to keep total suite time reasonable.

## 6. Running Benchmarks

### Local Development

```bash
# Run only benchmarks
pytest tests/benchmark_*.py --benchmark-only

# Run benchmarks with comparison against saved baseline
pytest tests/benchmark_*.py --benchmark-only --benchmark-compare

# Save current results as baseline
pytest tests/benchmark_*.py --benchmark-only --benchmark-save=baseline

# Generate JSON report
pytest tests/benchmark_*.py --benchmark-only --benchmark-json=results.json
```

### CI/CD Integration

```bash
# In CI: compare against main branch baseline
pytest tests/benchmark_*.py --benchmark-only --benchmark-compare=baseline --benchmark-fail-fast
```

## 7. Success Criteria

The benchmark implementation is complete when:

1. [ ] `pytest-benchmark` is added to dev dependencies
2. [ ] Three benchmark files exist with comprehensive test coverage
3. [ ] All benchmarks pass and produce valid statistics
4. [ ] Benchmarks are skipped by default in regular test runs
5. [ ] README or docs include instructions for running benchmarks
6. [ ] No production dependencies are added
7. [ ] Existing functional tests remain unaffected

## 8. Future Enhancements (Out of Scope)

The following are identified but deferred to future work:

- **ASV (airspeed velocity) integration**: For long-term trend tracking across commits
- **Memory profiling**: Using `pytest-memray` or `memory_profiler`
- **Profiling integration**: Generate cProfile stats for slow benchmarks
- **Benchmark dashboards**: Upload results to external visualization service
- **Parametrized archive sizes**: Test extraction across multiple size tiers (1MB, 10MB, 100MB, 1GB)

## 9. References

- [pytest-benchmark documentation](https://pytest-benchmark.readthedocs.io/)
- [try7z AGENTS.md](C:/Users/24238/Desktop/try7z/AGENTS.md)
- [try7z extractor.py](C:/Users/24238/Desktop/try7z/try7z/extractor.py)
- [try7z password_manager.py](C:/Users/24238/Desktop/try7z/try7z/password_manager.py)
