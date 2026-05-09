"""Benchmark tests for Extractor performance."""

from pathlib import Path

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from try7z.extractor import Extractor

from .conftest import generate_passwords


class TestBenchmarkPasswordAttempts:
    """Benchmark password attempt speed."""

    @pytest.mark.benchmark(min_rounds=1, max_time=10.0)
    def test_benchmark_password_not_in_list_large(
        self, encrypted_7z_archive: Path, temp_dir: Path, benchmark: BenchmarkFixture
    ) -> None:
        """Benchmark: 1000 wrong passwords (all fail)."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"
        passwords = generate_passwords(1000)

        result = benchmark(extractor.try_extract, output_dir, passwords)

        assert result[0] is False
        assert result[1] is None

    @pytest.mark.benchmark(min_rounds=1, max_time=5.0)
    def test_benchmark_password_not_in_list_small(
        self, encrypted_7z_archive: Path, temp_dir: Path, benchmark: BenchmarkFixture
    ) -> None:
        """Benchmark: 10 wrong passwords (all fail)."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"
        passwords = generate_passwords(10)

        result = benchmark(extractor.try_extract, output_dir, passwords)

        assert result[0] is False
        assert result[1] is None

    @pytest.mark.benchmark(min_rounds=1, max_time=5.0)
    def test_benchmark_password_at_start(
        self, encrypted_7z_archive: Path, temp_dir: Path, benchmark: BenchmarkFixture
    ) -> None:
        """Benchmark: correct password at index 0 (best case)."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"
        passwords = generate_passwords(100, correct="secret123", correct_index=0)

        result = benchmark(extractor.try_extract, output_dir, passwords)

        assert result[0] is True
        assert result[1] == "secret123"

    @pytest.mark.benchmark(min_rounds=1, max_time=5.0)
    def test_benchmark_password_at_end(
        self, encrypted_7z_archive: Path, temp_dir: Path, benchmark: BenchmarkFixture
    ) -> None:
        """Benchmark: correct password at index 99 (worst case)."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"
        passwords = generate_passwords(100, correct="secret123", correct_index=99)

        result = benchmark(extractor.try_extract, output_dir, passwords)

        assert result[0] is True
        assert result[1] == "secret123"


class TestBenchmarkArchiveExtraction:
    """Benchmark archive extraction speed."""

    @pytest.mark.benchmark(min_rounds=1, max_time=5.0)
    def test_benchmark_extract_plain_7z(
        self, plain_7z_archive: Path, temp_dir: Path, benchmark: BenchmarkFixture
    ) -> None:
        """Benchmark: extract plain (non-encrypted) 7z archive."""
        extractor = Extractor(plain_7z_archive)
        output_dir = temp_dir / "output"

        result = benchmark(extractor.try_extract, output_dir)

        assert result[0] is True
        assert result[1] is None

    @pytest.mark.benchmark(min_rounds=1, max_time=5.0)
    def test_benchmark_extract_encrypted_7z(
        self, encrypted_7z_archive: Path, temp_dir: Path, benchmark: BenchmarkFixture
    ) -> None:
        """Benchmark: extract encrypted 7z with correct password."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"
        passwords = ["secret123"]

        result = benchmark(extractor.try_extract, output_dir, passwords)

        assert result[0] is True
        assert result[1] == "secret123"

    @pytest.mark.benchmark(min_rounds=1, max_time=10.0)
    def test_benchmark_extract_large_archive(
        self, large_7z_archive: Path, temp_dir: Path, benchmark: BenchmarkFixture
    ) -> None:
        """Benchmark: extract large (~50MB) 7z archive."""
        extractor = Extractor(large_7z_archive)
        output_dir = temp_dir / "output"

        result = benchmark(extractor.try_extract, output_dir)

        assert result[0] is True
        assert result[1] is None
