"""Shared pytest fixtures."""

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
