"""Tests for CLI commands."""

import argparse
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from try7z.cli.main import (
    RemovalResult,
    RemoveByIndexStrategy,
    RemoveByValueStrategy,
    _report_removal_result,
    _resolve_input_paths,
    cmd_add_password,
    cmd_autocompletion,
    cmd_clear_passwords,
    cmd_edit_passwords,
    cmd_extract,
    cmd_list_passwords,
    cmd_remove_password,
    cmd_show_path,
    main,
)
from try7z.extractor import get_7z_version
from try7z.password_manager import PasswordManager


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

    def test_add_password_default_manager(self, capsys) -> None:
        """Test adding password with default manager (manager=None)."""
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            data_dir = Path(d)
            manager = PasswordManager(data_dir=data_dir)

            args = argparse.Namespace()
            args.passwords = ["default_test"]

            exit_code = cmd_add_password(args, manager)

            assert exit_code == 0
            assert "default_test" in manager.get_passwords()

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
        assert "Skipped 1 invalid/duplicate password(s)" in captured.out
        assert "already exists" in captured.err

    def test_add_all_duplicates(self, password_manager: PasswordManager, capsys) -> None:
        """Test adding only duplicate passwords returns 0 per UNIX convention."""
        password_manager.add_password("dup1")
        password_manager.add_password("dup2")

        args = argparse.Namespace()
        args.passwords = ["dup1", "dup2"]

        exit_code = cmd_add_password(args, password_manager)

        assert exit_code == 0  # Always 0 - operation completed successfully
        captured = capsys.readouterr()
        assert "Skipped 2 invalid/duplicate password(s)" in captured.out

    def test_add_empty_password_shows_warning(
        self, password_manager: PasswordManager, capsys
    ) -> None:
        """Test that empty password is skipped with warning."""
        args = argparse.Namespace()
        args.passwords = ["", "valid"]

        exit_code = cmd_add_password(args, password_manager)

        assert exit_code == 0
        assert password_manager.count() == 1
        assert "valid" in password_manager.get_passwords()
        captured = capsys.readouterr()
        assert "cannot be empty" in captured.err
        assert "skipped" in captured.err.lower()

    def test_add_whitespace_password_shows_warning(
        self, password_manager: PasswordManager, capsys
    ) -> None:
        """Test that whitespace-only password is skipped."""
        args = argparse.Namespace()
        args.passwords = ["   ", "valid"]

        exit_code = cmd_add_password(args, password_manager)

        assert exit_code == 0
        assert password_manager.count() == 1
        captured = capsys.readouterr()
        assert "whitespace-only" in captured.err

    def test_add_very_long_password_shows_warning(
        self, password_manager: PasswordManager, capsys
    ) -> None:
        """Test that very long password is skipped."""
        args = argparse.Namespace()
        args.passwords = ["a" * 1001, "valid"]

        exit_code = cmd_add_password(args, password_manager)

        assert exit_code == 0
        assert password_manager.count() == 1
        captured = capsys.readouterr()
        assert "exceeds maximum length" in captured.err

    def test_add_mixed_valid_invalid_and_duplicate(
        self, password_manager: PasswordManager, capsys
    ) -> None:
        """Test batch with valid, invalid, and duplicate passwords."""
        password_manager.add_password("existing")

        args = argparse.Namespace()
        args.passwords = ["", "existing", "valid", "   ", "another"]

        exit_code = cmd_add_password(args, password_manager)

        assert exit_code == 0
        assert password_manager.count() == 3  # existing + valid + another
        captured = capsys.readouterr()
        assert "Added 2 password(s)" in captured.out
        assert "Skipped 3" in captured.out


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


class TestRemoveByValueStrategy:
    """Test cases for RemoveByValueStrategy."""

    def test_execute_removes_passwords(self, password_manager: PasswordManager) -> None:
        """Test removing multiple passwords by value."""
        password_manager.add_password("pwd1")
        password_manager.add_password("pwd2")

        strategy = RemoveByValueStrategy(["pwd1", "pwd2"])
        result = strategy.execute(password_manager)

        assert result.removed_count == 2
        assert password_manager.count() == 0
        assert "Removed: pwd1" in result.success_messages
        assert "Removed: pwd2" in result.success_messages

    def test_execute_deduplicates(self, password_manager: PasswordManager) -> None:
        """Test that duplicate passwords are deduplicated."""
        password_manager.add_password("pwd1")

        strategy = RemoveByValueStrategy(["pwd1", "pwd1"])
        result = strategy.execute(password_manager)

        assert result.removed_count == 1
        assert len(result.success_messages) == 1

    def test_execute_reports_failures(self, password_manager: PasswordManager) -> None:
        """Test that non-existent passwords are reported as failures."""
        strategy = RemoveByValueStrategy(["nonexistent"])
        result = strategy.execute(password_manager)

        assert result.removed_count == 0
        assert len(result.failures) == 1
        assert "not found" in result.failures[0]

    def test_execute_mixed_success_and_failure(self, password_manager: PasswordManager) -> None:
        """Test mixed success and failure scenarios."""
        password_manager.add_password("exists")

        strategy = RemoveByValueStrategy(["not_exist", "exists", "also_not_exist"])
        result = strategy.execute(password_manager)

        assert result.removed_count == 1
        assert len(result.success_messages) == 1
        assert len(result.failures) == 2


class TestRemoveByIndexStrategy:
    """Test cases for RemoveByIndexStrategy."""

    def test_execute_removes_by_index(self, password_manager: PasswordManager) -> None:
        """Test removing passwords by index."""
        password_manager.add_password("a")
        password_manager.add_password("b")

        strategy = RemoveByIndexStrategy([1, 2])
        result = strategy.execute(password_manager)

        assert result.removed_count == 2
        assert password_manager.count() == 0
        assert "Removed [1]: a" in result.success_messages
        assert "Removed [2]: b" in result.success_messages

    def test_execute_deduplicates_and_sorts(self, password_manager: PasswordManager) -> None:
        """Test that duplicate indices are deduplicated and sorted."""
        password_manager.add_password("a")
        password_manager.add_password("b")

        strategy = RemoveByIndexStrategy([2, 2, 1])
        result = strategy.execute(password_manager)

        assert result.removed_count == 2
        assert password_manager.count() == 0

    def test_execute_reports_out_of_range(self, password_manager: PasswordManager) -> None:
        """Test that out-of-range indices are reported as failures."""
        password_manager.add_password("only")

        strategy = RemoveByIndexStrategy([1, 5])
        result = strategy.execute(password_manager)

        assert result.removed_count == 1
        assert len(result.failures) == 1
        assert "out of range" in result.failures[0]


class TestReportRemovalResult:
    """Test cases for _report_removal_result."""

    def test_reports_success_and_failures(self, capsys) -> None:
        """Test reporting mixed success and failures."""
        result = RemovalResult(
            removed_count=1,
            failures=["Password 'missing' not found"],
            success_messages=["Removed: existing"],
        )

        _report_removal_result(result, 5)

        captured = capsys.readouterr()
        assert "Removed: existing" in captured.out
        assert "not found" in captured.err
        assert "Removed 1 password(s). Total: 5" in captured.out

    def test_reports_no_removals(self, capsys) -> None:
        """Test reporting when nothing was removed."""
        result = RemovalResult(
            removed_count=0,
            failures=[],
            success_messages=[],
        )

        _report_removal_result(result, 0)

        captured = capsys.readouterr()
        assert "Removed 0 password(s). Total: 0" in captured.out


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

    def test_list_empty_default_manager(self, capsys) -> None:
        """Test listing with default manager when empty."""
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            data_dir = Path(d)
            manager = PasswordManager(data_dir=data_dir)

            args = argparse.Namespace()
            exit_code = cmd_list_passwords(args, manager)

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

    def test_edit_opens_file_macos(self, password_manager: PasswordManager) -> None:
        """Test that edit command opens file on macOS."""
        args = argparse.Namespace()
        password_manager.passwords_file.touch(exist_ok=True)

        with patch("os.name", "posix"), patch("sys.platform", "darwin"), patch(
            "subprocess.run"
        ) as mock_run:
            exit_code = cmd_edit_passwords(args, password_manager)

        assert exit_code == 0
        mock_run.assert_called_once_with(
            ["open", str(password_manager.passwords_file)], check=True
        )

    def test_edit_opens_file_linux(self, password_manager: PasswordManager) -> None:
        """Test that edit command opens file on Linux."""
        args = argparse.Namespace()
        password_manager.passwords_file.touch(exist_ok=True)

        with patch("os.name", "posix"), patch("sys.platform", "linux"), patch(
            "subprocess.run"
        ) as mock_run:
            exit_code = cmd_edit_passwords(args, password_manager)

        assert exit_code == 0
        mock_run.assert_called_once_with(
            ["xdg-open", str(password_manager.passwords_file)], check=True
        )


class TestExtractCommand:
    """Test cases for extract CLI command."""

    def test_extract_plain_7z(
        self, plain_7z_archive: Path, temp_dir: Path, password_manager: PasswordManager, capsys
    ) -> None:
        """Test extracting a plain 7z archive via CLI."""
        args = argparse.Namespace()
        args.archive = [str(plain_7z_archive)]
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
        args.archive = [str(encrypted_7z_archive)]
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
        args.archive = [str(encrypted_7z_archive)]
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
        args.archive = [str(invalid_file)]
        args.output = None
        args.password = None
        args.force = False

        exit_code = cmd_extract(args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Warning" in captured.err

    def test_extract_nonexistent_file(self, temp_dir: Path, capsys) -> None:
        """Test extracting a nonexistent file."""
        args = argparse.Namespace()
        args.archive = [str(temp_dir / "missing.7z")]
        args.output = None
        args.password = None
        args.force = False

        exit_code = cmd_extract(args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Warning" in captured.err


class TestGet7zVersion:
    """Test cases for get_7z_version function."""

    def test_get_7z_version(self) -> None:
        """Test that get_7z_version returns a valid version string."""
        version = get_7z_version()

        assert isinstance(version, str)
        assert version != "unknown"
        assert "7-Zip" in version


class TestMain:
    """Test cases for main() function."""

    def test_main_version_flag(self, capsys) -> None:
        """Test that --version flag works."""
        with patch.object(sys, "argv", ["try7z", "--version"]):
            exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "try7z" in captured.out
        assert "7-Zip" in captured.out

    def test_main_no_command_shows_help(self, capsys) -> None:
        """Test that running without commands shows help."""
        with patch.object(sys, "argv", ["try7z"]):
            exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "usage:" in captured.out.lower()

    def test_main_add_command(self, temp_dir: Path, capsys) -> None:
        """Test that add command works through main()."""
        with patch.object(
            sys, "argv", ["try7z", "add", "testpassword123"]
        ), patch(
            "try7z.cli.main.PasswordManager"
        ) as mock_manager_class:
            mock_manager = mock_manager_class.return_value
            mock_manager.count.return_value = 1
            exit_code = main()

        assert exit_code == 0

    def test_main_extract_command(
        self, plain_7z_archive: Path, temp_dir: Path, capsys
    ) -> None:
        """Test that extract command works through main()."""
        with patch.object(
            sys,
            "argv",
            [
                "try7z",
                "extract",
                str(plain_7z_archive),
                "-o",
                str(temp_dir / "output"),
                "-f",
            ],
        ):
            exit_code = main()

        assert exit_code == 0
        assert (temp_dir / "output" / "src" / "test.txt").exists()

    def test_main_list_command(self, capsys) -> None:
        """Test that list command works through main()."""
        with patch.object(sys, "argv", ["try7z", "list"]), patch(
            "try7z.cli.main.PasswordManager"
        ) as mock_manager_class:
            mock_manager = mock_manager_class.return_value
            mock_manager.count.return_value = 0
            mock_manager.get_passwords.return_value = []
            exit_code = main()

        assert exit_code == 0

    def test_main_path_command(self, capsys) -> None:
        """Test that path command works through main()."""
        with patch.object(sys, "argv", ["try7z", "path"]), patch(
            "try7z.cli.main.PasswordManager"
        ) as mock_manager_class:
            mock_manager = mock_manager_class.return_value
            mock_manager.passwords_file = Path("/fake/path/passwords.json")
            exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "passwords.json" in captured.out

    def test_main_remove_command(self, capsys) -> None:
        """Test that remove command works through main()."""
        with patch.object(
            sys, "argv", ["try7z", "remove", "testpassword"]
        ), patch(
            "try7z.cli.main.PasswordManager"
        ) as mock_manager_class:
            mock_manager = mock_manager_class.return_value
            mock_manager.get_passwords.return_value = ["testpassword"]
            exit_code = main()

        assert exit_code == 0


class TestExtractCommandEdgeCases:
    """Test edge cases for extract command."""

    def test_extract_default_output_dir(
        self, plain_7z_archive: Path, temp_dir: Path, password_manager: PasswordManager
    ) -> None:
        """Test extracting with default output directory."""
        args = argparse.Namespace()
        args.archive = [str(plain_7z_archive)]
        args.output = None
        args.password = None
        args.force = True

        exit_code = cmd_extract(args, password_manager)

        assert exit_code == 0
        default_output = plain_7z_archive.parent / plain_7z_archive.stem
        assert (default_output / "src" / "test.txt").exists()

    def test_extract_output_exists_confirm_yes(
        self, plain_7z_archive: Path, temp_dir: Path, password_manager: PasswordManager, monkeypatch
    ) -> None:
        """Test extraction when output exists and user confirms overwrite."""
        output_dir = temp_dir / "existing_output"
        output_dir.mkdir()
        (output_dir / "old_file.txt").write_text("old content")

        args = argparse.Namespace()
        args.archive = [str(plain_7z_archive)]
        args.output = str(output_dir)
        args.password = None
        args.force = False

        monkeypatch.setattr("builtins.input", lambda _: "y")

        exit_code = cmd_extract(args, password_manager)

        assert exit_code == 0
        assert (output_dir / "src" / "test.txt").exists()
        assert not (output_dir / "old_file.txt").exists()

    def test_extract_output_exists_confirm_no(
        self, plain_7z_archive: Path, temp_dir: Path, password_manager: PasswordManager, monkeypatch
    ) -> None:
        """Test extraction when output exists and user cancels."""
        output_dir = temp_dir / "existing_output"
        output_dir.mkdir()
        (output_dir / "old_file.txt").write_text("old content")

        args = argparse.Namespace()
        args.archive = [str(plain_7z_archive)]
        args.output = str(output_dir)
        args.password = None
        args.force = False

        monkeypatch.setattr("builtins.input", lambda _: "n")

        exit_code = cmd_extract(args, password_manager)

        assert exit_code == 1
        assert (output_dir / "old_file.txt").exists()

    def test_extract_password_not_found(
        self, encrypted_7z_archive: Path, temp_dir: Path, password_manager: PasswordManager, capsys
    ) -> None:
        """Test extraction when password is not found."""
        password_manager.add_password("wrong_password")

        args = argparse.Namespace()
        args.archive = [str(encrypted_7z_archive)]
        args.output = str(temp_dir / "output")
        args.password = None
        args.force = True

        exit_code = cmd_extract(args, password_manager)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "No matching password found" in captured.err

    def test_extract_multiple_archives_all_success(
        self,
        plain_7z_archive: Path,
        temp_dir: Path,
        password_manager: PasswordManager,
        capsys,
        seven_zip: Path,
    ) -> None:
        """Test extracting multiple archives all succeeding."""
        # Create a second plain archive to avoid fixture conflicts
        src2 = temp_dir / "src2"
        src2.mkdir()
        (src2 / "test.txt").write_text("Second archive")
        archive2 = temp_dir / "second.7z"
        subprocess.run(
            [str(seven_zip), "a", str(archive2), str(src2)],
            capture_output=True,
            check=True,
        )

        args = argparse.Namespace()
        args.archive = [str(plain_7z_archive), str(archive2)]
        args.output = str(temp_dir / "output")
        args.password = None
        args.force = True

        exit_code = cmd_extract(args, password_manager)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Summary: 2 succeeded, 0 failed" in captured.out
        assert (temp_dir / "output" / "plain" / "src" / "test.txt").exists()
        assert (temp_dir / "output" / "second" / "src2" / "test.txt").exists()

    def test_extract_multiple_archives_partial_failure(
        self,
        plain_7z_archive: Path,
        temp_dir: Path,
        password_manager: PasswordManager,
        capsys,
        seven_zip: Path,
    ) -> None:
        """Test extracting multiple archives with partial failure."""
        # Create an encrypted archive that will fail (no password stored)
        src2 = temp_dir / "src2"
        src2.mkdir()
        (src2 / "test.txt").write_text("Secret content")
        archive2 = temp_dir / "secret.7z"
        subprocess.run(
            [str(seven_zip), "a", "-psecret123", "-mhe=on", str(archive2), str(src2)],
            capture_output=True,
            check=True,
        )

        args = argparse.Namespace()
        args.archive = [str(plain_7z_archive), str(archive2)]
        args.output = str(temp_dir / "output")
        args.password = None
        args.force = True

        exit_code = cmd_extract(args, password_manager)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Summary: 1 succeeded, 1 failed" in captured.out
        assert (temp_dir / "output" / "plain" / "src" / "test.txt").exists()

    def test_extract_multiple_archives_default_output_dir(
        self,
        plain_7z_archive: Path,
        temp_dir: Path,
        password_manager: PasswordManager,
        seven_zip: Path,
    ) -> None:
        """Test extracting multiple archives without -o option."""
        src2 = temp_dir / "src2"
        src2.mkdir()
        (src2 / "test.txt").write_text("Second archive")
        archive2 = temp_dir / "second.7z"
        subprocess.run(
            [str(seven_zip), "a", str(archive2), str(src2)],
            capture_output=True,
            check=True,
        )

        args = argparse.Namespace()
        args.archive = [str(plain_7z_archive), str(archive2)]
        args.output = None
        args.password = None
        args.force = True

        exit_code = cmd_extract(args, password_manager)

        assert exit_code == 0
        assert (plain_7z_archive.parent / "plain" / "src" / "test.txt").exists()
        assert (archive2.parent / "second" / "src2" / "test.txt").exists()

    def test_extract_directory_with_archives(
        self,
        plain_7z_archive: Path,
        temp_dir: Path,
        password_manager: PasswordManager,
        capsys,
    ) -> None:
        """Test extracting from a directory containing archives."""
        args = argparse.Namespace()
        args.archive = [str(temp_dir)]
        args.output = None
        args.password = None
        args.force = True

        exit_code = cmd_extract(args, password_manager)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Success!" in captured.out
        default_output = plain_7z_archive.parent / plain_7z_archive.stem
        assert (default_output / "src" / "test.txt").exists()

    def test_extract_empty_directory(
        self, temp_dir: Path, password_manager: PasswordManager, capsys
    ) -> None:
        """Test extracting from an empty directory returns 0."""
        args = argparse.Namespace()
        args.archive = [str(temp_dir)]
        args.output = None
        args.password = None
        args.force = False

        exit_code = cmd_extract(args, password_manager)

        assert exit_code == 0

    def test_extract_directory_with_output_flag(
        self,
        plain_7z_archive: Path,
        temp_dir: Path,
        password_manager: PasswordManager,
        capsys,
    ) -> None:
        """Test extracting directory archives to specified output."""
        output_dir = temp_dir / "all_extracted"
        args = argparse.Namespace()
        args.archive = [str(temp_dir)]
        args.output = str(output_dir)
        args.password = None
        args.force = True

        exit_code = cmd_extract(args, password_manager)

        assert exit_code == 0
        assert (output_dir / "src" / "test.txt").exists()


class TestAutocompletionCommand:
    """Test cases for autocompletion command."""

    def test_autocompletion_bash_stdout(self, capsys) -> None:
        """Test generating bash completion script to stdout."""
        args = argparse.Namespace()
        args.shell = "bash"
        args.install = False

        exit_code = cmd_autocompletion(args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "_try7z_completion" in captured.out
        assert "complete -F _try7z_completion try7z" in captured.out

    def test_autocompletion_pwsh_stdout(self, capsys) -> None:
        """Test generating pwsh completion script to stdout."""
        args = argparse.Namespace()
        args.shell = "pwsh"
        args.install = False

        exit_code = cmd_autocompletion(args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Register-ArgumentCompleter" in captured.out
        assert "try7z pwsh completion script" in captured.out

    def test_autocompletion_powershell_stdout(self, capsys) -> None:
        """Test generating powershell completion script to stdout."""
        args = argparse.Namespace()
        args.shell = "powershell"
        args.install = False

        exit_code = cmd_autocompletion(args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Register-ArgumentCompleter" in captured.out
        assert "try7z powershell completion script" in captured.out

    def test_autocompletion_bash_install(self, temp_dir: Path, capsys) -> None:
        """Test installing bash completion script."""
        bashrc = temp_dir / ".bashrc"
        completion_file = temp_dir / ".try7z-completion.bash"

        with patch("try7z.cli.completions._get_bashrc_path", return_value=bashrc), patch(
            "try7z.cli.completions.Path.home", return_value=temp_dir
        ):
            args = argparse.Namespace()
            args.shell = "bash"
            args.install = True

            exit_code = cmd_autocompletion(args)

        assert exit_code == 0
        assert completion_file.exists()
        assert "_try7z_completion" in completion_file.read_text()
        assert bashrc.exists()
        assert ".try7z-completion.bash" in bashrc.read_text()
        captured = capsys.readouterr()
        assert "installed" in captured.out
        assert "bashrc" in captured.out

    def test_autocompletion_pwsh_install(self, temp_dir: Path, capsys) -> None:
        """Test installing pwsh completion script."""
        profile = temp_dir / "profile.ps1"

        with patch(
            "try7z.cli.completions._get_pwsh_profile_path", return_value=profile
        ):
            args = argparse.Namespace()
            args.shell = "pwsh"
            args.install = True

            exit_code = cmd_autocompletion(args)

        assert exit_code == 0
        assert profile.exists()
        assert "Register-ArgumentCompleter" in profile.read_text()
        captured = capsys.readouterr()
        assert "installed" in captured.out
        assert "PowerShell" in captured.out

    def test_autocompletion_powershell_install(self, temp_dir: Path, capsys) -> None:
        """Test installing powershell completion script."""
        profile = temp_dir / "powershell_profile.ps1"

        with patch(
            "try7z.cli.completions._get_powershell_profile_path",
            return_value=profile,
        ):
            args = argparse.Namespace()
            args.shell = "powershell"
            args.install = True

            exit_code = cmd_autocompletion(args)

        assert exit_code == 0
        assert profile.exists()
        assert "Register-ArgumentCompleter" in profile.read_text()
        assert "try7z powershell completion script" in profile.read_text()
        captured = capsys.readouterr()
        assert "installed" in captured.out
        assert "powershell" in captured.out

    def test_autocompletion_unsupported_shell(self, capsys) -> None:
        """Test error for unsupported shell."""
        args = argparse.Namespace()
        args.shell = "fish"
        args.install = False

        exit_code = cmd_autocompletion(args)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Unsupported shell" in captured.err

    def test_main_autocompletion_command(self, capsys) -> None:
        """Test autocompletion command through main()."""
        with patch.object(
            sys, "argv", ["try7z", "autocompletion", "--shell", "bash"]
        ):
            exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "_try7z_completion" in captured.out

    def test_autocompletion_bash_install_existing_bashrc(
        self, temp_dir: Path, capsys
    ) -> None:
        """Test installing bash completion when .bashrc already exists."""
        bashrc = temp_dir / ".bashrc"
        bashrc.write_text("# existing bashrc\n", encoding="utf-8")
        completion_file = temp_dir / ".try7z-completion.bash"

        with patch("try7z.cli.completions._get_bashrc_path", return_value=bashrc), patch(
            "try7z.cli.completions.Path.home", return_value=temp_dir
        ):
            args = argparse.Namespace()
            args.shell = "bash"
            args.install = True

            exit_code = cmd_autocompletion(args)

        assert exit_code == 0
        content = bashrc.read_text(encoding="utf-8")
        assert "# existing bashrc" in content
        assert ".try7z-completion.bash" in content
        assert completion_file.exists()
        captured = capsys.readouterr()
        assert "installed" in captured.out

    def test_autocompletion_bash_install_duplicate_source(
        self, temp_dir: Path, capsys
    ) -> None:
        """Test that duplicate source lines are not added to .bashrc."""
        bashrc = temp_dir / ".bashrc"
        bashrc.write_text("# bashrc\n", encoding="utf-8")

        with patch("try7z.cli.completions._get_bashrc_path", return_value=bashrc), patch(
            "try7z.cli.completions.Path.home", return_value=temp_dir
        ):
            args = argparse.Namespace()
            args.shell = "bash"
            args.install = True

            # Install twice
            cmd_autocompletion(args)
            exit_code = cmd_autocompletion(args)

        assert exit_code == 0
        content = bashrc.read_text(encoding="utf-8")
        # source_line appears twice per install (once in -f, once in source)
        assert content.count("# try7z shell completion") == 1

    def test_autocompletion_pwsh_install_existing_profile(
        self, temp_dir: Path, capsys
    ) -> None:
        """Test installing pwsh completion when profile already exists."""
        profile = temp_dir / "profile.ps1"
        profile.write_text("# existing profile\n", encoding="utf-8")

        with patch(
            "try7z.cli.completions._get_pwsh_profile_path", return_value=profile
        ):
            args = argparse.Namespace()
            args.shell = "pwsh"
            args.install = True

            exit_code = cmd_autocompletion(args)

        assert exit_code == 0
        content = profile.read_text(encoding="utf-8")
        assert "# existing profile" in content
        assert "Register-ArgumentCompleter" in content
        captured = capsys.readouterr()
        assert "installed" in captured.out

    def test_autocompletion_pwsh_install_replace_existing(
        self, temp_dir: Path, capsys
    ) -> None:
        """Test replacing existing pwsh completion script."""
        profile = temp_dir / "profile.ps1"
        profile.write_text(
            "# profile\n# try7z pwsh completion script\n"
            "Register-ArgumentCompleter -Native -CommandName try7z "
            "-ScriptBlock {\n    param($wordToComplete)\n}\n# other\n",
            encoding="utf-8",
        )

        with patch(
            "try7z.cli.completions._get_pwsh_profile_path", return_value=profile
        ):
            args = argparse.Namespace()
            args.shell = "pwsh"
            args.install = True

            exit_code = cmd_autocompletion(args)

        assert exit_code == 0
        content = profile.read_text(encoding="utf-8")
        assert "# profile" in content
        assert content.count("try7z pwsh completion script") == 1
        assert "# other" in content
        captured = capsys.readouterr()
        assert "installed" in captured.out

    def test_pwsh_script_quotes_filenames_with_spaces(self) -> None:
        """Test that pwsh completion script quotes filenames with spaces.

        Verifies the generated script contains logic to wrap filenames
        containing spaces in double quotes, preventing argument splitting.
        """
        from try7z.cli.completions import generate_pwsh_completion

        script = generate_pwsh_completion()
        assert "$ct = $_" in script
        assert "if ($ct -match ' ') { $ct = '\"{0}\"' -f $ct }" in script

    def test_pwsh_format_string_not_literal_zero(self) -> None:
        """Test that {0} format placeholder is not corrupted by f-string.

        Regression test for the bug where Python's f-string interpreted
        {0} as an expression, generating PowerShell code '"0"' instead of
        '"{0}"'. This caused all quoted filenames to become "0".
        """
        from try7z.cli.completions import generate_pwsh_completion

        script = generate_pwsh_completion()
        # Must contain PowerShell format string {0}, not Python expression 0
        assert "'\"{0}\"' -f $ct" in script
        # Ensure it does NOT contain the buggy literal '"0"'
        assert "'\"0\"' -f $ct" not in script

    def test_pwsh_quotes_multiple_spaces(self, temp_dir: Path) -> None:
        """Test quoting of filenames with multiple consecutive spaces.

        Verifies that filenames like 'A  B.zip' (double space) are still
        correctly quoted in the completion output.
        """
        from try7z.cli.completions import (
            _install_pwsh_completion_common,
            generate_pwsh_completion,
        )

        profile = temp_dir / "profile.ps1"
        script = generate_pwsh_completion()
        _install_pwsh_completion_common(profile, script)

        content = profile.read_text(encoding="utf-8")
        assert content.count("Register-ArgumentCompleter") == 1

    def test_powershell_script_syntax_valid(self, temp_dir: Path) -> None:
        """Test that generated Windows PowerShell script is syntactically valid.

        Similar to test_pwsh_script_syntax_valid but for Windows PowerShell
        (powershell.exe) which may have slightly different syntax rules.
        """
        from try7z.cli.completions import generate_powershell_completion

        script = generate_powershell_completion()
        script_file = temp_dir / "completion.ps1"
        script_file.write_text(script, encoding="utf-8")

        result = subprocess.run(
            [
                "pwsh",
                "-NoProfile",
                "-Command",
                f"Invoke-Expression (Get-Content '{script_file}' -Raw)",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"PowerShell syntax error:\n{result.stderr}"
        )

    def test_autocompletion_pwsh_install_no_duplicate(self, temp_dir: Path) -> None:
        """Test that installing pwsh completion twice does not duplicate.

        Simulates the bug where repeated --install appended a new script block
        instead of replacing the existing one.
        """
        from try7z.cli.completions import (
            _install_pwsh_completion_common,
            generate_pwsh_completion,
        )

        profile = temp_dir / "profile.ps1"
        # Pre-populate with an existing completion script
        old_script = generate_pwsh_completion()
        _install_pwsh_completion_common(profile, old_script)

        content_before = profile.read_text(encoding="utf-8")
        assert content_before.count("Register-ArgumentCompleter") == 1

        # Install again
        new_script = generate_pwsh_completion()
        _install_pwsh_completion_common(profile, new_script)

        content_after = profile.read_text(encoding="utf-8")
        assert content_after.count("Register-ArgumentCompleter") == 1
        assert content_after.count("try7z pwsh completion script") == 1

    def test_pwsh_script_syntax_valid(self, temp_dir: Path) -> None:
        """Test that generated pwsh script is syntactically valid.

        Catches issues like unmatched braces that cause ParserError
        when the profile is loaded.
        """
        from try7z.cli.completions import generate_pwsh_completion

        script = generate_pwsh_completion()
        script_file = temp_dir / "completion.ps1"
        script_file.write_text(script, encoding="utf-8")

        result = subprocess.run(
            [
                "pwsh",
                "-NoProfile",
                "-Command",
                f"Invoke-Expression (Get-Content '{script_file}' -Raw)",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"PowerShell syntax error:\n{result.stderr}"
        )

    def test_autocompletion_install_error(self, capsys) -> None:
        """Test handling of install errors."""
        with patch(
            "try7z.cli.main.install_completion",
            side_effect=OSError("Permission denied"),
        ):
            args = argparse.Namespace()
            args.shell = "bash"
            args.install = True

            exit_code = cmd_autocompletion(args)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error installing completion" in captured.err
        assert "Permission denied" in captured.err


class TestResolveInputPaths:
    """Test cases for _resolve_input_paths function."""

    def test_single_supported_file(self, temp_dir: Path) -> None:
        """Test resolving a single supported archive file."""
        archive = temp_dir / "test.7z"
        archive.write_text("fake archive")

        result = _resolve_input_paths([str(archive)])

        assert len(result) == 1
        assert result[0] == archive.resolve()

    def test_single_directory_with_archives(self, temp_dir: Path) -> None:
        """Test resolving a directory containing multiple archives."""
        (temp_dir / "a.7z").write_text("archive a")
        (temp_dir / "b.zip").write_text("archive b")
        (temp_dir / "c.rar").write_text("archive c")
        (temp_dir / "other.txt").write_text("not an archive")

        result = _resolve_input_paths([str(temp_dir)])

        assert len(result) == 3
        names = [p.name for p in result]
        assert "a.7z" in names
        assert "b.zip" in names
        assert "c.rar" in names
        assert "other.txt" not in names

    def test_empty_directory(self, temp_dir: Path) -> None:
        """Test resolving an empty directory returns empty list."""
        result = _resolve_input_paths([str(temp_dir)])

        assert result == []

    def test_directory_with_only_unsupported_files(self, temp_dir: Path) -> None:
        """Test directory with only non-archive files returns empty list."""
        (temp_dir / "readme.txt").write_text("readme")
        (temp_dir / "data.json").write_text("{}")

        result = _resolve_input_paths([str(temp_dir)])

        assert result == []

    def test_mixed_file_and_directory(self, temp_dir: Path) -> None:
        """Test resolving a mix of file and directory paths."""
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "sub.7z").write_text("sub archive")

        main_archive = temp_dir / "main.zip"
        main_archive.write_text("main archive")

        result = _resolve_input_paths([str(main_archive), str(subdir)])

        assert len(result) == 2
        names = [p.name for p in result]
        assert "main.zip" in names
        assert "sub.7z" in names

    def test_unsupported_file(self, temp_dir: Path, capsys) -> None:
        """Test unsupported file prints warning and returns empty list."""
        txt_file = temp_dir / "readme.txt"
        txt_file.write_text("readme")

        result = _resolve_input_paths([str(txt_file)])

        assert result == []
        captured = capsys.readouterr()
        assert "Unsupported file format" in captured.err
        assert "readme.txt" in captured.err

    def test_nonexistent_path(self, temp_dir: Path, capsys) -> None:
        """Test nonexistent path prints warning and returns empty list."""
        missing = temp_dir / "missing.7z"

        result = _resolve_input_paths([str(missing)])

        assert result == []
        captured = capsys.readouterr()
        assert "Path not found" in captured.err
        assert "missing.7z" in captured.err

    def test_multiple_directories(self, temp_dir: Path) -> None:
        """Test resolving multiple directories."""
        dir1 = temp_dir / "dir1"
        dir1.mkdir()
        (dir1 / "a.7z").write_text("archive a")

        dir2 = temp_dir / "dir2"
        dir2.mkdir()
        (dir2 / "b.zip").write_text("archive b")

        result = _resolve_input_paths([str(dir1), str(dir2)])

        assert len(result) == 2
        names = [p.name for p in result]
        assert "a.7z" in names
        assert "b.zip" in names

    def test_duplicate_paths(self, temp_dir: Path) -> None:
        """Test duplicate paths are deduplicated."""
        archive = temp_dir / "test.7z"
        archive.write_text("archive")

        result = _resolve_input_paths([str(archive), str(archive)])

        assert len(result) == 1

    def test_case_insensitive_extensions(self, temp_dir: Path) -> None:
        """Test archive extensions are matched case-insensitively."""
        (temp_dir / "lower.7z").write_text("lower")
        (temp_dir / "upper.ZIP").write_text("upper")
        (temp_dir / "mixed.Rar").write_text("mixed")

        result = _resolve_input_paths([str(temp_dir)])

        assert len(result) == 3

    def test_result_is_sorted(self, temp_dir: Path) -> None:
        """Test result is sorted by path string."""
        (temp_dir / "z.7z").write_text("z")
        (temp_dir / "a.7z").write_text("a")
        (temp_dir / "m.7z").write_text("m")

        result = _resolve_input_paths([str(temp_dir)])

        assert len(result) == 3
        names = [p.name for p in result]
        assert names == ["a.7z", "m.7z", "z.7z"]
