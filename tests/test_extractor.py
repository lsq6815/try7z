"""Tests for Extractor."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from autopasstryunzip.extractor import Extractor, get_7z_path
from autopasstryunzip.utils import InvalidArchiveError, PasswordNotFoundError


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


@pytest.fixture
def plain_zip_archive(temp_dir: Path, seven_zip: Path) -> Path:
    """Create a plain (non-encrypted) zip archive for testing."""
    src_dir = temp_dir / "src"
    src_dir.mkdir()
    (src_dir / "test.txt").write_text("Hello, ZIP!")

    archive_path = temp_dir / "plain.zip"
    subprocess.run(
        [str(seven_zip), "a", str(archive_path), str(src_dir)],
        capture_output=True,
        check=True,
    )
    return archive_path


@pytest.fixture
def encrypted_zip_archive(temp_dir: Path, seven_zip: Path) -> Path:
    """Create an encrypted zip archive for testing."""
    src_dir = temp_dir / "src"
    src_dir.mkdir()
    (src_dir / "test.txt").write_text("Secret ZIP content!")

    archive_path = temp_dir / "encrypted.zip"
    subprocess.run(
        [str(seven_zip), "a", "-pzipsecret", str(archive_path), str(src_dir)],
        capture_output=True,
        check=True,
    )
    return archive_path


class TestExtractor:
    """Test cases for Extractor."""

    def test_init_with_valid_archive(self, plain_7z_archive: Path) -> None:
        """Test initialization with valid archive."""
        extractor = Extractor(plain_7z_archive)
        assert extractor.archive_path == plain_7z_archive.resolve()

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

    def test_extract_plain_7z_archive(self, plain_7z_archive: Path, temp_dir: Path) -> None:
        """Test extracting a plain 7z archive."""
        extractor = Extractor(plain_7z_archive)
        output_dir = temp_dir / "output"

        success, password = extractor.try_extract(output_dir)

        assert success is True
        assert password is None
        assert (output_dir / "src" / "test.txt").exists()

    def test_extract_encrypted_7z_with_password_list(
        self, encrypted_7z_archive: Path, temp_dir: Path
    ) -> None:
        """Test extracting encrypted 7z with a list of passwords."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"
        passwords = ["wrong1", "wrong2", "secret123", "wrong3"]

        success, used_password = extractor.try_extract(output_dir, passwords)

        assert success is True
        assert used_password == "secret123"
        assert (output_dir / "src" / "test.txt").exists()

    def test_extract_wrong_password_raises(
        self, encrypted_7z_archive: Path, temp_dir: Path
    ) -> None:
        """Test that wrong passwords raise PasswordNotFoundError."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"
        wrong_passwords = ["wrong1", "wrong2", "wrong3"]

        with pytest.raises(PasswordNotFoundError):
            extractor.extract_with_passwords(wrong_passwords, output_dir)

    def test_extract_creates_output_dir(self, plain_7z_archive: Path, temp_dir: Path) -> None:
        """Test that extraction creates output directory."""
        extractor = Extractor(plain_7z_archive)
        output_dir = temp_dir / "new_output"

        assert not output_dir.exists()
        extractor.try_extract(output_dir)
        assert output_dir.exists()

    def test_extract_plain_zip_archive(self, plain_zip_archive: Path, temp_dir: Path) -> None:
        """Test extracting a plain zip archive."""
        extractor = Extractor(plain_zip_archive)
        output_dir = temp_dir / "output"

        success, password = extractor.try_extract(output_dir)

        assert success is True
        assert password is None
        assert (output_dir / "src" / "test.txt").exists()

    def test_extract_encrypted_zip_with_password(
        self, encrypted_zip_archive: Path, temp_dir: Path
    ) -> None:
        """Test extracting encrypted zip with correct password."""
        extractor = Extractor(encrypted_zip_archive)
        output_dir = temp_dir / "output"

        success, used_password = extractor.try_extract(output_dir, ["zipsecret"])

        assert success is True
        assert used_password == "zipsecret"
        assert (output_dir / "src" / "test.txt").exists()

    @pytest.mark.parametrize(
        "passwords,expected_password",
        [
            (["secret123", "wrong1", "wrong2"], "secret123"),
            (["wrong1", "secret123", "wrong2"], "secret123"),
            (["wrong1", "wrong2", "secret123"], "secret123"),
        ],
    )
    def test_extract_encrypted_7z_password_positions(
        self,
        encrypted_7z_archive: Path,
        temp_dir: Path,
        passwords: list[str],
        expected_password: str,
    ) -> None:
        """Test extracting encrypted 7z with password at various positions."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"

        success, used_password = extractor.try_extract(output_dir, passwords)

        assert success is True
        assert used_password == expected_password
        assert (output_dir / "src" / "test.txt").exists()

    @pytest.mark.parametrize(
        "passwords,expected_password",
        [
            (["zipsecret", "wrong1", "wrong2"], "zipsecret"),
            (["wrong1", "zipsecret", "wrong2"], "zipsecret"),
            (["wrong1", "wrong2", "zipsecret"], "zipsecret"),
        ],
    )
    def test_extract_encrypted_zip_password_positions(
        self,
        encrypted_zip_archive: Path,
        temp_dir: Path,
        passwords: list[str],
        expected_password: str,
    ) -> None:
        """Test extracting encrypted zip with password at various positions."""
        extractor = Extractor(encrypted_zip_archive)
        output_dir = temp_dir / "output"

        success, used_password = extractor.try_extract(output_dir, passwords)

        assert success is True
        assert used_password == expected_password
        assert (output_dir / "src" / "test.txt").exists()

    def test_extract_encrypted_7z_password_not_in_list(
        self, encrypted_7z_archive: Path, temp_dir: Path
    ) -> None:
        """Test extracting encrypted 7z when password is not in list."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"
        wrong_passwords = ["wrong1", "wrong2", "wrong3"]

        success, used_password = extractor.try_extract(output_dir, wrong_passwords)

        assert success is False
        assert used_password is None

    def test_extract_encrypted_zip_password_not_in_list(
        self, encrypted_zip_archive: Path, temp_dir: Path
    ) -> None:
        """Test extracting encrypted zip when password is not in list."""
        extractor = Extractor(encrypted_zip_archive)
        output_dir = temp_dir / "output"
        wrong_passwords = ["wrong1", "wrong2", "wrong3"]

        success, used_password = extractor.try_extract(output_dir, wrong_passwords)

        assert success is False
        assert used_password is None

    def test_extract_encrypted_7z_single_correct_password(
        self, encrypted_7z_archive: Path, temp_dir: Path
    ) -> None:
        """Test extracting encrypted 7z with single correct password."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"

        success, used_password = extractor.try_extract(output_dir, ["secret123"])

        assert success is True
        assert used_password == "secret123"
        assert (output_dir / "src" / "test.txt").exists()

    def test_extract_encrypted_7z_single_wrong_password(
        self, encrypted_7z_archive: Path, temp_dir: Path
    ) -> None:
        """Test extracting encrypted 7z with single wrong password."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "output"

        success, used_password = extractor.try_extract(output_dir, ["wrongpassword"])

        assert success is False
        assert used_password is None

    def test_extract_encrypted_zip_single_wrong_password(
        self, encrypted_zip_archive: Path, temp_dir: Path
    ) -> None:
        """Test extracting encrypted zip with single wrong password."""
        extractor = Extractor(encrypted_zip_archive)
        output_dir = temp_dir / "output"

        success, used_password = extractor.try_extract(output_dir, ["wrongpassword"])

        assert success is False
        assert used_password is None

    def test_try_extract_failure_no_empty_dir(
        self, encrypted_7z_archive: Path, temp_dir: Path
    ) -> None:
        """Test that try_extract does not leave empty dir on failure."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "should_not_exist"

        success, used_password = extractor.try_extract(
            output_dir, ["wrong1", "wrong2"]
        )

        assert success is False
        assert used_password is None
        assert not output_dir.exists()

    def test_extract_with_passwords_failure_no_empty_dir(
        self, encrypted_7z_archive: Path, temp_dir: Path
    ) -> None:
        """Test that extract_with_passwords does not leave empty dir on failure."""
        extractor = Extractor(encrypted_7z_archive)
        output_dir = temp_dir / "should_not_exist"

        with pytest.raises(PasswordNotFoundError):
            extractor.extract_with_passwords(["wrong1", "wrong2"], output_dir)

        assert not output_dir.exists()
