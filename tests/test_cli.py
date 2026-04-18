"""Tests for CLI commands."""

import argparse
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from try7z.extractor import get_7z_path, get_7z_version
from try7z.main import (
    cmd_add_password,
    cmd_clear_passwords,
    cmd_edit_passwords,
    cmd_extract,
    cmd_list_passwords,
    cmd_remove_password,
    cmd_show_path,
)
from try7z.password_manager import PasswordManager


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def password_manager(temp_dir: Path) -> PasswordManager:
    """Create a PasswordManager with temporary directory."""
    return PasswordManager(data_dir=temp_dir)


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


class TestAddCommand:
    """Test cases for add command."""

    def test_add_single_password(self, password_manager: PasswordManager, capsys) -> None:
        """Test adding a single password."""
        args = argparse.Namespace()
        args.passwords = ["test123"]

        exit_code = cmd_add_password(args, password_manager)

        assert exit_code == 0
        assert "test123" in password_manager.get_passwords()
        captured = capsys.readouterr()
        assert "Added 1 password(s)" in captured.out

    def test_add_multiple_passwords(self, password_manager: PasswordManager, capsys) -> None:
        """Test adding multiple passwords at once."""
        args = argparse.Namespace()
        args.passwords = ["pwd1", "pwd2", "pwd3"]

        exit_code = cmd_add_password(args, password_manager)

        assert exit_code == 0
        assert password_manager.count() == 3
        captured = capsys.readouterr()
        assert "Added 3 password(s)" in captured.out

    def test_add_with_duplicates(self, password_manager: PasswordManager, capsys) -> None:
        """Test adding passwords with some duplicates."""
        password_manager.add_password("existing")

        args = argparse.Namespace()
        args.passwords = ["existing", "new1", "new2"]

        exit_code = cmd_add_password(args, password_manager)

        assert exit_code == 0
        assert password_manager.count() == 3
        captured = capsys.readouterr()
        assert "Added 2 password(s)" in captured.out
        assert "Skipped 1 duplicate(s)" in captured.out
        assert "already exists" in captured.err

    def test_add_all_duplicates(self, password_manager: PasswordManager, capsys) -> None:
        """Test adding only duplicate passwords."""
        password_manager.add_password("dup1")
        password_manager.add_password("dup2")

        args = argparse.Namespace()
        args.passwords = ["dup1", "dup2"]

        exit_code = cmd_add_password(args, password_manager)

        assert exit_code == 1  # Non-zero because nothing was added
        captured = capsys.readouterr()
        assert "Skipped 2 duplicate(s)" in captured.out


class TestRemoveCommand:
    """Test cases for remove command."""

    def test_remove_by_value_single(self, password_manager: PasswordManager, capsys) -> None:
        """Test removing a single password by value."""
        password_manager.add_password("test123")

        args = argparse.Namespace()
        args.password = ["test123"]
        args.index = None

        exit_code = cmd_remove_password(args, password_manager)

        assert exit_code == 0
        assert "test123" not in password_manager.get_passwords()
        captured = capsys.readouterr()
        assert "Removed: test123" in captured.out

    def test_remove_by_value_multiple(self, password_manager: PasswordManager, capsys) -> None:
        """Test removing multiple passwords by value."""
        password_manager.add_password("pwd1")
        password_manager.add_password("pwd2")
        password_manager.add_password("pwd3")

        args = argparse.Namespace()
        args.password = ["pwd1", "pwd3"]
        args.index = None

        exit_code = cmd_remove_password(args, password_manager)

        assert exit_code == 0
        assert password_manager.get_passwords() == ["pwd2"]
        captured = capsys.readouterr()
        assert "Removed 2 password(s)" in captured.out

    def test_remove_by_value_partial_not_found(
        self, password_manager: PasswordManager, capsys
    ) -> None:
        """Test removing with some passwords not found."""
        password_manager.add_password("exists")

        args = argparse.Namespace()
        args.password = ["not_exist", "exists", "also_not_exist"]
        args.index = None

        exit_code = cmd_remove_password(args, password_manager)

        assert exit_code == 0
        assert password_manager.count() == 0
        captured = capsys.readouterr()
        assert "Removed: exists" in captured.out
        assert "not found" in captured.err
        assert "also_not_exist" in captured.err

    def test_remove_by_index_single(self, password_manager: PasswordManager, capsys) -> None:
        """Test removing a single password by index."""
        password_manager.add_password("first")
        password_manager.add_password("second")

        args = argparse.Namespace()
        args.password = []
        args.index = [2]  # 1-based, removes "second"

        exit_code = cmd_remove_password(args, password_manager)

        assert exit_code == 0
        assert password_manager.get_passwords() == ["first"]
        captured = capsys.readouterr()
        assert "Removed [2]: second" in captured.out

    def test_remove_by_index_multiple(self, password_manager: PasswordManager, capsys) -> None:
        """Test removing multiple passwords by index."""
        password_manager.add_password("a")
        password_manager.add_password("b")
        password_manager.add_password("c")
        password_manager.add_password("d")

        args = argparse.Namespace()
        args.password = []
        args.index = [1, 3]  # Removes "a" and "c"

        exit_code = cmd_remove_password(args, password_manager)

        assert exit_code == 0
        assert password_manager.get_passwords() == ["b", "d"]
        captured = capsys.readouterr()
        assert "Removed 2 password(s)" in captured.out

    def test_remove_by_index_partial_invalid(
        self, password_manager: PasswordManager, capsys
    ) -> None:
        """Test removing with some indices out of range."""
        password_manager.add_password("only")

        args = argparse.Namespace()
        args.password = []
        args.index = [1, 5, 10]  # Only 1 is valid

        exit_code = cmd_remove_password(args, password_manager)

        assert exit_code == 0
        assert password_manager.count() == 0
        captured = capsys.readouterr()
        assert "Removed [1]: only" in captured.out
        assert "Index 5 out of range" in captured.err
        assert "Index 10 out of range" in captured.err

    def test_remove_both_value_and_index_error(self, capsys) -> None:
        """Test error when both value and index are provided."""
        args = argparse.Namespace()
        args.password = ["test"]
        args.index = [1]

        exit_code = cmd_remove_password(args)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Cannot use both" in captured.err

    def test_remove_neither_value_nor_index_error(self, capsys) -> None:
        """Test error when neither value nor index is provided."""
        args = argparse.Namespace()
        args.password = []
        args.index = None

        exit_code = cmd_remove_password(args)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Please specify" in captured.err


class TestPathCommand:
    """Test cases for path command."""

    def test_show_path(self, password_manager: PasswordManager, capsys) -> None:
        """Test showing passwords file path."""
        args = argparse.Namespace()

        exit_code = cmd_show_path(args, password_manager)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert str(password_manager.passwords_file) in captured.out
        assert "passwords.json" in captured.out


class TestListCommand:
    """Test cases for list command."""

    def test_list_empty(self, password_manager: PasswordManager, capsys) -> None:
        """Test listing when no passwords are stored."""
        args = argparse.Namespace()

        exit_code = cmd_list_passwords(args, password_manager)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "No passwords stored" in captured.out

    def test_list_with_passwords(self, password_manager: PasswordManager, capsys) -> None:
        """Test listing stored passwords with indices."""
        password_manager.add_password("first")
        password_manager.add_password("second")
        password_manager.add_password("third")

        args = argparse.Namespace()

        exit_code = cmd_list_passwords(args, password_manager)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Stored passwords (3)" in captured.out
        assert "1. first" in captured.out
        assert "2. second" in captured.out
        assert "3. third" in captured.out


class TestClearCommand:
    """Test cases for clear command."""

    def test_clear_with_force(self, password_manager: PasswordManager, capsys) -> None:
        """Test clearing passwords with force flag."""
        password_manager.add_password("test")
        args = argparse.Namespace()
        args.force = True

        exit_code = cmd_clear_passwords(args, password_manager)

        assert exit_code == 0
        assert password_manager.count() == 0
        captured = capsys.readouterr()
        assert "All passwords cleared" in captured.out

    def test_clear_with_confirmation_yes(
        self, password_manager: PasswordManager, capsys, monkeypatch
    ) -> None:
        """Test clearing with user confirming 'y'."""
        password_manager.add_password("test")
        args = argparse.Namespace()
        args.force = False
        monkeypatch.setattr("builtins.input", lambda _: "y")

        exit_code = cmd_clear_passwords(args, password_manager)

        assert exit_code == 0
        assert password_manager.count() == 0
        captured = capsys.readouterr()
        assert "All passwords cleared" in captured.out

    def test_clear_with_confirmation_no(
        self, password_manager: PasswordManager, capsys, monkeypatch
    ) -> None:
        """Test clearing with user cancelling."""
        password_manager.add_password("test")
        args = argparse.Namespace()
        args.force = False
        monkeypatch.setattr("builtins.input", lambda _: "n")

        exit_code = cmd_clear_passwords(args, password_manager)

        assert exit_code == 0
        assert password_manager.count() == 1
        captured = capsys.readouterr()
        assert "Cancelled" in captured.out


class TestEditCommand:
    """Test cases for edit command."""

    def test_edit_opens_file(self, password_manager: PasswordManager) -> None:
        """Test that edit command opens the passwords file."""
        args = argparse.Namespace()
        password_manager.passwords_file.touch(exist_ok=True)

        with patch("os.startfile") as mock_startfile:
            exit_code = cmd_edit_passwords(args, password_manager)

        assert exit_code == 0
        mock_startfile.assert_called_once_with(str(password_manager.passwords_file))

    def test_edit_error(self, password_manager: PasswordManager, capsys) -> None:
        """Test that edit command handles errors gracefully."""
        args = argparse.Namespace()
        password_manager.passwords_file.touch(exist_ok=True)

        with patch("os.startfile", side_effect=OSError("Access denied")):
            exit_code = cmd_edit_passwords(args, password_manager)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error opening file" in captured.err


class TestExtractCommand:
    """Test cases for extract CLI command."""

    def test_extract_plain_7z(
        self, plain_7z_archive: Path, temp_dir: Path, password_manager: PasswordManager, capsys
    ) -> None:
        """Test extracting a plain 7z archive via CLI."""
        args = argparse.Namespace()
        args.archive = str(plain_7z_archive)
        args.output = str(temp_dir / "output")
        args.password = None
        args.force = True

        exit_code = cmd_extract(args, password_manager)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Success!" in captured.out
        assert (temp_dir / "output" / "src" / "test.txt").exists()

    def test_extract_encrypted_7z_with_stored_password(
        self, encrypted_7z_archive: Path, temp_dir: Path, password_manager: PasswordManager, capsys
    ) -> None:
        """Test extracting encrypted 7z with stored password."""
        password_manager.add_password("secret123")

        args = argparse.Namespace()
        args.archive = str(encrypted_7z_archive)
        args.output = str(temp_dir / "output")
        args.password = None
        args.force = True

        exit_code = cmd_extract(args, password_manager)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Success!" in captured.out
        assert (temp_dir / "output" / "src" / "test.txt").exists()

    def test_extract_with_priority_password(
        self, encrypted_7z_archive: Path, temp_dir: Path, password_manager: PasswordManager, capsys
    ) -> None:
        """Test extracting with a priority password."""
        args = argparse.Namespace()
        args.archive = str(encrypted_7z_archive)
        args.output = str(temp_dir / "output")
        args.password = "secret123"
        args.force = True

        exit_code = cmd_extract(args, password_manager)

        assert exit_code == 0
        assert (temp_dir / "output" / "src" / "test.txt").exists()

    def test_extract_invalid_archive(self, temp_dir: Path, capsys) -> None:
        """Test extracting an invalid archive."""
        invalid_file = temp_dir / "not_an_archive.txt"
        invalid_file.write_text("not an archive")

        args = argparse.Namespace()
        args.archive = str(invalid_file)
        args.output = None
        args.password = None
        args.force = False

        exit_code = cmd_extract(args)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err

    def test_extract_nonexistent_file(self, temp_dir: Path, capsys) -> None:
        """Test extracting a nonexistent file."""
        args = argparse.Namespace()
        args.archive = str(temp_dir / "missing.7z")
        args.output = None
        args.password = None
        args.force = False

        exit_code = cmd_extract(args)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err


class TestGet7zVersion:
    """Test cases for get_7z_version function."""

    def test_get_7z_version(self) -> None:
        """Test that get_7z_version returns a valid version string."""
        version = get_7z_version()

        assert isinstance(version, str)
        assert version != "unknown"
        assert "7-Zip" in version
