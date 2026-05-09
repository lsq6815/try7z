"""Shared pytest fixtures."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from try7z.extractor import get_7z_path


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def seven_zip() -> Path:
    """Get path to 7z executable."""
    return get_7z_path()


@pytest.fixture
def plain_7z_archive(temp_dir: Path, seven_zip: Path) -> Path:
    """Create a plain (non-encrypted) 7z archive for testing."""
    src_dir = temp_dir / "src"
    src_dir.mkdir()
    (src_dir / "test.txt").write_text("Hello, World!")

    archive_path = temp_dir / "plain.7z"
    subprocess.run(
        [str(seven_zip), "a", str(archive_path), str(src_dir)],
        capture_output=True,
        check=True,
    )
    return archive_path


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


@pytest.fixture
def encrypted_7z_archive(temp_dir: Path, seven_zip: Path) -> Path:
    """Create an encrypted 7z archive for testing."""
    src_dir = temp_dir / "src"
    src_dir.mkdir()
    (src_dir / "test.txt").write_text("Secret content!")

    archive_path = temp_dir / "encrypted.7z"
    subprocess.run(
        [str(seven_zip), "a", "-psecret123", "-mhe=on", str(archive_path), str(src_dir)],
        capture_output=True,
        check=True,
    )
    return archive_path


def generate_passwords(
    count: int,
    correct: str | None = None,
    correct_index: int | None = None,
) -> list[str]:
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
        if not (0 <= correct_index < count):
            raise ValueError(
                f"correct_index must be in range [0, {count}), got {correct_index}"
            )
        passwords[correct_index] = correct
    return passwords
