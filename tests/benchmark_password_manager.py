"""Benchmark tests for PasswordManager performance."""

import json
import uuid
from pathlib import Path

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from try7z.password_manager import PasswordManager


def _clear_passwords_file(temp_dir: Path) -> None:
    """Remove passwords.json if it exists."""
    passwords_file = temp_dir / "passwords.json"
    if passwords_file.exists():
        passwords_file.unlink()


class TestBenchmarkPasswordManagerCrud:
    """Benchmark password manager CRUD operations."""

    @pytest.mark.benchmark(min_rounds=1, max_time=5.0)
    def test_benchmark_add_password(self, temp_dir: Path, benchmark: BenchmarkFixture) -> None:
        """Benchmark: add a single password."""
        def _add_password() -> None:
            _clear_passwords_file(temp_dir)
            manager = PasswordManager(data_dir=temp_dir, auto_save=False)
            manager.add_password(f"test_{uuid.uuid4().hex[:8]}")

        benchmark(_add_password)

    @pytest.mark.benchmark(min_rounds=1, max_time=5.0)
    def test_benchmark_add_passwords_batch(
        self, temp_dir: Path, benchmark: BenchmarkFixture
    ) -> None:
        """Benchmark: add 100 passwords with auto_save=False."""
        passwords = [f"pwd_{i}" for i in range(100)]

        def _batch_add() -> None:
            _clear_passwords_file(temp_dir)
            manager = PasswordManager(data_dir=temp_dir, auto_save=False)
            for pwd in passwords:
                manager.add_password(pwd)
            manager.save()

        benchmark(_batch_add)

    @pytest.mark.benchmark(min_rounds=1, max_time=5.0)
    def test_benchmark_get_passwords_small(
        self, temp_dir: Path, benchmark: BenchmarkFixture
    ) -> None:
        """Benchmark: get passwords list (10 items)."""
        _clear_passwords_file(temp_dir)
        manager = PasswordManager(data_dir=temp_dir, auto_save=False)
        for i in range(10):
            manager.add_password(f"pwd_{i}")
        manager.save()

        result = benchmark(manager.get_passwords)

        assert len(result) == 10

    @pytest.mark.benchmark(min_rounds=1, max_time=5.0)
    def test_benchmark_get_passwords_large(
        self, temp_dir: Path, benchmark: BenchmarkFixture
    ) -> None:
        """Benchmark: get passwords list (10,000 items)."""
        _clear_passwords_file(temp_dir)
        manager = PasswordManager(data_dir=temp_dir, auto_save=False)
        for i in range(10000):
            manager.add_password(f"pwd_{i}")
        manager.save()

        result = benchmark(manager.get_passwords)

        assert len(result) == 10000

    @pytest.mark.benchmark(min_rounds=1, max_time=5.0)
    def test_benchmark_remove_password(self, temp_dir: Path, benchmark: BenchmarkFixture) -> None:
        """Benchmark: remove password by value from 100-item list."""
        def _remove() -> PasswordManager:
            _clear_passwords_file(temp_dir)
            manager = PasswordManager(data_dir=temp_dir, auto_save=False)
            for i in range(100):
                manager.add_password(f"pwd_{i}")
            manager.save()
            manager.remove_password("pwd_50")
            return manager

        manager = benchmark(_remove)
        assert "pwd_50" not in manager.get_passwords()

    @pytest.mark.benchmark(min_rounds=1, max_time=5.0)
    def test_benchmark_remove_by_index(self, temp_dir: Path, benchmark: BenchmarkFixture) -> None:
        """Benchmark: remove password by index from 100-item list."""
        def _remove() -> PasswordManager:
            _clear_passwords_file(temp_dir)
            manager = PasswordManager(data_dir=temp_dir, auto_save=False)
            for i in range(100):
                manager.add_password(f"pwd_{i}")
            manager.save()
            manager.remove_by_index(50)
            return manager

        manager = benchmark(_remove)
        assert len(manager.get_passwords()) == 99


class TestBenchmarkPasswordManagerPersistence:
    """Benchmark password manager persistence operations."""

    @pytest.mark.benchmark(min_rounds=1, max_time=5.0)
    def test_benchmark_load_passwords(self, temp_dir: Path, benchmark: BenchmarkFixture) -> None:
        """Benchmark: load 10,000 passwords from JSON file."""
        passwords_data = {"passwords": [f"pwd_{i}" for i in range(10000)]}
        passwords_file = temp_dir / "passwords.json"
        passwords_file.write_text(json.dumps(passwords_data))

        def load_manager() -> PasswordManager:
            return PasswordManager(data_dir=temp_dir)

        manager = benchmark(load_manager)

        assert manager.count() == 10000

    @pytest.mark.benchmark(min_rounds=1, max_time=5.0)
    def test_benchmark_save_passwords(self, temp_dir: Path, benchmark: BenchmarkFixture) -> None:
        """Benchmark: save 10,000 passwords to JSON file."""
        def _save() -> PasswordManager:
            _clear_passwords_file(temp_dir)
            manager = PasswordManager(data_dir=temp_dir, auto_save=False)
            for i in range(10000):
                manager.add_password(f"pwd_{i}")
            manager.save()
            return manager

        benchmark(_save)
        passwords_file = temp_dir / "passwords.json"
        assert passwords_file.exists()
        data = json.loads(passwords_file.read_text())
        assert len(data["passwords"]) == 10000
