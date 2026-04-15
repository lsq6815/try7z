"""Tests for Extractor."""

import tempfile
from pathlib import Path

import py7zr
import pytest

from src.extractor import Extractor
from src.utils import InvalidArchiveError, PasswordNotFoundError


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def plain_archive(temp_dir: Path) -> Path:
    """Create a plain (non-encrypted) archive for testing."""
    src_dir = temp_dir / "src"
    src_dir.mkdir()
    (src_dir / "test.txt").write_text("Hello, World!")

    archive_path = temp_dir / "plain.7z"
    with py7zr.SevenZipFile(archive_path, "w") as archive:
        archive.writeall(src_dir, "src")
    return archive_path


@pytest.fixture
def encrypted_archive(temp_dir: Path) -> Path:
    """Create an encrypted archive for testing."""
    src_dir = temp_dir / "src"
    src_dir.mkdir()
    (src_dir / "test.txt").write_text("Secret content!")

    archive_path = temp_dir / "encrypted.7z"
    with py7zr.SevenZipFile(archive_path, "w", password="secret123") as archive:
        archive.writeall(src_dir, "src")
    return archive_path


class TestExtractor:
    """Test cases for Extractor."""

    def test_init_with_valid_archive(self, plain_archive: Path) -> None:
        """Test initialization with valid archive."""
        extractor = Extractor(plain_archive)
        assert extractor.archive_path == plain_archive.resolve()

    def test_init_with_nonexistent_file(self, temp_dir: Path) -> None:
        """Test that nonexistent file raises error."""
        with pytest.raises(InvalidArchiveError, match="not found"):
            Extractor(temp_dir / "nonexistent.7z")

    def test_init_with_unsupported_format(self, temp_dir: Path) -> None:
        """Test that unsupported format raises error."""
        unsupported_file = temp_dir / "test.xyz"
        unsupported_file.write_text("not an archive")
        with pytest.raises(InvalidArchiveError, match="Unsupported"):
            Extractor(unsupported_file)

    def test_extract_plain_archive(self, plain_archive: Path, temp_dir: Path) -> None:
        """Test extracting a plain archive."""
        extractor = Extractor(plain_archive)
        output_dir = temp_dir / "output"

        success, password = extractor.try_extract(output_dir)

        assert success is True
        assert password is None
        assert (output_dir / "src" / "test.txt").exists()

    def test_extract_with_password_list(self, encrypted_archive: Path, temp_dir: Path) -> None:
        """Test extracting with a list of passwords."""
        extractor = Extractor(encrypted_archive)
        output_dir = temp_dir / "output"
        passwords = ["wrong1", "wrong2", "secret123", "wrong3"]

        success, used_password = extractor.try_extract(output_dir, passwords)

        assert success is True
        assert used_password == "secret123"

    def test_extract_wrong_password_raises(self, encrypted_archive: Path, temp_dir: Path) -> None:
        """Test that wrong passwords raise PasswordNotFoundError."""
        extractor = Extractor(encrypted_archive)
        output_dir = temp_dir / "output"
        wrong_passwords = ["wrong1", "wrong2", "wrong3"]

        with pytest.raises(PasswordNotFoundError):
            extractor.extract_with_passwords(wrong_passwords, output_dir)

    def test_extract_creates_output_dir(self, plain_archive: Path, temp_dir: Path) -> None:
        """Test that extraction creates output directory."""
        extractor = Extractor(plain_archive)
        output_dir = temp_dir / "new_output"

        assert not output_dir.exists()
        extractor.try_extract(output_dir)
        assert output_dir.exists()
