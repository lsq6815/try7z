"""Tests for CLI commands."""

import argparse
import tempfile
from pathlib import Path

import pytest

from autopasstryunzip.main import (
    cmd_add_password,
    cmd_remove_password,
    cmd_show_path,
)
from autopasstryunzip.password_manager import PasswordManager


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def password_manager(temp_dir: Path) -> PasswordManager:
    """Create a PasswordManager with temporary directory."""
    return PasswordManager(data_dir=temp_dir)


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
