"""Benchmark tests for end-to-end CLI performance."""

import shutil
import subprocess
import sys
from pathlib import Path

from pytest_benchmark.fixture import BenchmarkFixture


class TestBenchmarkCliExtraction:
    """Benchmark complete CLI extraction workflows."""

    def test_benchmark_cli_extract_plain(
        self, plain_7z_archive: Path, temp_dir: Path, benchmark: BenchmarkFixture
    ) -> None:
        """Benchmark: CLI extraction of plain archive."""
        output_dir = temp_dir / "output"

        def run_extract() -> subprocess.CompletedProcess[str]:
            shutil.rmtree(output_dir, ignore_errors=True)
            return subprocess.run(
                [
                    sys.executable, "-m", "try7z",
                    "extract", str(plain_7z_archive),
                    "-o", str(output_dir),
                    "-f",
                ],
                capture_output=True,
                text=True,
            )

        result = benchmark(run_extract)

        assert result.returncode == 0
        assert "Success" in result.stdout

    def test_benchmark_cli_extract_encrypted(
        self, encrypted_7z_archive: Path, temp_dir: Path, benchmark: BenchmarkFixture
    ) -> None:
        """Benchmark: CLI extraction of encrypted archive."""
        output_dir = temp_dir / "output"

        def run_extract() -> subprocess.CompletedProcess[str]:
            shutil.rmtree(output_dir, ignore_errors=True)
            return subprocess.run(
                [
                    sys.executable, "-m", "try7z",
                    "extract", str(encrypted_7z_archive),
                    "-o", str(output_dir),
                    "-f", "-p", "secret123",
                ],
                capture_output=True,
                text=True,
            )

        result = benchmark(run_extract)

        assert result.returncode == 0
        assert "Success" in result.stdout


