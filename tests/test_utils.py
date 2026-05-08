"""Tests for utility functions."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from try7z.utils import (
    SUPPORTED_EXTENSIONS,
    InvalidArchiveError,
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
        with patch.dict("os.environ", {"APPDATA": r"C:\Users\Test\AppData\Roaming"}):
            with patch("sys.platform", "win32"):
                result = get_user_data_dir()
                assert result == Path(r"C:\Users\Test\AppData\Roaming\try7z")

    def test_get_user_data_dir_windows_no_appdata(self) -> None:
        """Test Windows fallback when APPDATA not set."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("sys.platform", "win32"):
                with patch.object(Path, "home", return_value=Path("/home/test")):
                    result = get_user_data_dir()
                    assert result == Path("/home/test/AppData/Roaming/try7z")

    def test_get_user_data_dir_darwin(self) -> None:
        """Test macOS data directory."""
        with patch("sys.platform", "darwin"):
            with patch.object(Path, "home", return_value=Path("/Users/test")):
                result = get_user_data_dir()
                assert result == Path("/Users/test/Library/Application Support/try7z")

    def test_get_user_data_dir_linux(self) -> None:
        """Test Linux data directory."""
        with patch("sys.platform", "linux"):
            with patch.object(Path, "home", return_value=Path("/home/test")):
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
        from try7z.utils import BasicPasswordValidator, PasswordValidationError

        validator = BasicPasswordValidator()
        with pytest.raises(PasswordValidationError, match="cannot be empty"):
            validator.validate("")


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)
