"""Tests for utility functions."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from try7z.utils import (
    SUPPORTED_EXTENSIONS,
    BasicPasswordValidator,
    InvalidArchiveError,
    PasswordValidationError,
    get_package_root,
    get_supported_extensions,
    get_user_data_dir,
    is_supported_archive,
    validate_archive_path,
)


class TestValidateArchivePath:
    """Test cases for validate_archive_path."""

    def test_validate_archive_path_not_file(self, temp_dir: Path) -> None:
        """Test that a directory raises InvalidArchiveError."""
        with pytest.raises(InvalidArchiveError, match="not a file"):
            validate_archive_path(temp_dir)


class TestGetUserDataDir:
    """Test cases for get_user_data_dir."""

    def test_get_user_data_dir_windows(self) -> None:
        """Test Windows data directory resolution."""
        with patch.dict("os.environ", {"APPDATA": r"C:\Users\Test\AppData\Roaming"}), patch(
            "sys.platform", "win32"
        ):
            result = get_user_data_dir()
            assert result == Path(r"C:\Users\Test\AppData\Roaming\try7z")

    def test_get_user_data_dir_windows_no_appdata(self) -> None:
        """Test Windows fallback when APPDATA not set."""
        with patch.dict("os.environ", {}, clear=True), patch(
            "sys.platform", "win32"
        ), patch.object(Path, "home", return_value=Path("/home/test")):
            result = get_user_data_dir()
            assert result == Path("/home/test/AppData/Roaming/try7z")

    def test_get_user_data_dir_darwin(self) -> None:
        """Test macOS data directory."""
        with patch("sys.platform", "darwin"), patch.object(
            Path, "home", return_value=Path("/Users/test")
        ):
            result = get_user_data_dir()
            assert result == Path("/Users/test/Library/Application Support/try7z")

    def test_get_user_data_dir_linux(self) -> None:
        """Test Linux data directory."""
        with patch("sys.platform", "linux"), patch.object(
            Path, "home", return_value=Path("/home/test")
        ):
            result = get_user_data_dir()
            assert result == Path("/home/test/.local/share/try7z")


class TestSupportedExtensions:
    """Test cases for supported archive extensions."""

    def test_supported_extensions_constant(self) -> None:
        """Test that the constant contains expected extensions."""
        assert ".7z" in SUPPORTED_EXTENSIONS
        assert ".zip" in SUPPORTED_EXTENSIONS
        assert ".rar" in SUPPORTED_EXTENSIONS
        assert isinstance(SUPPORTED_EXTENSIONS, frozenset)

    def test_get_supported_extensions(self) -> None:
        """Test that get_supported_extensions returns expected values."""
        exts = get_supported_extensions()
        assert ".7z" in exts
        assert ".zip" in exts
        assert ".rar" in exts
        assert exts == set(SUPPORTED_EXTENSIONS)


class TestIsSupportedArchive:
    """Test cases for is_supported_archive."""

    def test_is_supported_archive_true(self) -> None:
        """Test that supported archives return True."""
        assert is_supported_archive(Path("test.7z")) is True
        assert is_supported_archive(Path("test.zip")) is True
        assert is_supported_archive(Path("test.rar")) is True

    def test_is_supported_archive_case_insensitive(self) -> None:
        """Test that extensions are case insensitive."""
        assert is_supported_archive(Path("test.ZIP")) is True
        assert is_supported_archive(Path("test.7Z")) is True

    def test_is_supported_archive_false(self) -> None:
        """Test that unsupported extensions return False."""
        assert is_supported_archive(Path("test.txt")) is False
        assert is_supported_archive(Path("test.pdf")) is False


class TestGetPackageRoot:
    """Test cases for get_package_root."""

    def test_get_package_root(self) -> None:
        """Test that package root is returned."""
        root = get_package_root()
        assert root.is_dir()
        assert (root / "utils.py").exists()


class TestBasicPasswordValidator:
    """Test cases for BasicPasswordValidator."""

    def test_validate_empty_string(self) -> None:
        """Test that empty string raises PasswordValidationError."""
        validator = BasicPasswordValidator()
        with pytest.raises(PasswordValidationError, match="cannot be empty"):
            validator.validate("")

    def test_validate_whitespace_only(self) -> None:
        """Test that whitespace-only password raises error."""
        validator = BasicPasswordValidator()
        with pytest.raises(PasswordValidationError, match="whitespace-only"):
            validator.validate("   ")

    def test_validate_whitespace_tabs_newlines(self) -> None:
        """Test that mixed whitespace raises error."""
        validator = BasicPasswordValidator()
        with pytest.raises(PasswordValidationError, match="whitespace-only"):
            validator.validate("  \t\n  ")

    def test_validate_max_length_exceeded(self) -> None:
        """Test that password exceeding max length raises error."""
        validator = BasicPasswordValidator()
        long_password = "a" * 1001
        with pytest.raises(PasswordValidationError, match="exceeds maximum length"):
            validator.validate(long_password)

    def test_validate_max_length_exactly_1000(self) -> None:
        """Test that password exactly 1000 chars is valid."""
        validator = BasicPasswordValidator()
        password_1000 = "a" * 1000
        validator.validate(password_1000)  # Should not raise

    def test_validate_valid_password(self) -> None:
        """Test that valid password passes validation."""
        validator = BasicPasswordValidator()
        validator.validate("valid_password123")  # Should not raise


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)
