"""Tests for PasswordManager."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from try7z.password_manager import PasswordManager
from try7z.utils import PasswordManagerError, PasswordValidationError


@pytest.fixture
def manager(temp_dir: Path) -> PasswordManager:
    """Create a PasswordManager with temporary directory."""
    return PasswordManager(data_dir=temp_dir)


class TestPasswordManager:
    """Test cases for PasswordManager."""

    def test_init_creates_data_dir(self, temp_dir: Path) -> None:
        """Test that initialization creates data directory."""
        new_dir = temp_dir / "new_data"
        PasswordManager(data_dir=new_dir)
        assert new_dir.exists()

    def test_add_password(self, manager: PasswordManager) -> None:
        """Test adding a password."""
        manager.add_password("test123")
        assert "test123" in manager.get_passwords()
        assert manager.count() == 1

    def test_add_duplicate_password_raises(self, manager: PasswordManager) -> None:
        """Test that adding duplicate password raises error."""
        manager.add_password("test123")
        with pytest.raises(PasswordManagerError, match="already exists"):
            manager.add_password("test123")

    def test_remove_password(self, manager: PasswordManager) -> None:
        """Test removing a password."""
        manager.add_password("test123")
        manager.remove_password("test123")
        assert "test123" not in manager.get_passwords()
        assert manager.count() == 0

    def test_remove_nonexistent_raises(self, manager: PasswordManager) -> None:
        """Test that removing nonexistent password raises error."""
        with pytest.raises(PasswordManagerError, match="not found"):
            manager.remove_password("nonexistent")

    def test_get_passwords_returns_copy(self, manager: PasswordManager) -> None:
        """Test that get_passwords returns a copy."""
        manager.add_password("test123")
        passwords = manager.get_passwords()
        passwords.append("new")
        assert "new" not in manager.get_passwords()

    def test_clear_passwords(self, manager: PasswordManager) -> None:
        """Test clearing all passwords."""
        manager.add_password("test1")
        manager.add_password("test2")
        manager.clear_passwords()
        assert manager.count() == 0

    def test_persistence(self, temp_dir: Path) -> None:
        """Test that passwords persist across instances."""
        manager1 = PasswordManager(data_dir=temp_dir)
        manager1.add_password("persist_test")

        manager2 = PasswordManager(data_dir=temp_dir)
        assert "persist_test" in manager2.get_passwords()

    def test_plain_text_storage(self, manager: PasswordManager) -> None:
        """Test that passwords are stored in plain text."""
        manager.add_password("secret_password")

        passwords_file = manager.passwords_file
        content = passwords_file.read_text(encoding="utf-8")
        data = json.loads(content)

        assert "secret_password" in data["passwords"]


class TestCorruptFile:
    """Test cases for corrupt passwords file handling."""

    def test_corrupt_json_raises_and_creates_backup(self, temp_dir: Path) -> None:
        """Test that corrupt JSON file raises error and creates backup."""
        passwords_file = temp_dir / "passwords.json"
        passwords_file.write_text("not valid json", encoding="utf-8")

        with pytest.raises(PasswordManagerError, match="corrupt"):
            PasswordManager(data_dir=temp_dir)

        # Check backup was created
        backup_file = passwords_file.with_suffix(".json.bak")
        assert backup_file.exists()
        assert backup_file.read_text(encoding="utf-8") == "not valid json"

    def test_corrupt_json_empties_passwords(self, temp_dir: Path) -> None:
        """Test that corrupt JSON results in empty password list."""
        passwords_file = temp_dir / "passwords.json"
        passwords_file.write_text("not valid json", encoding="utf-8")

        with pytest.raises(PasswordManagerError):
            PasswordManager(data_dir=temp_dir)

        # After the error, a new instance should start fresh
        # (the corrupt file was moved to backup)
        pm = PasswordManager(data_dir=temp_dir)
        assert pm.count() == 0

    def test_missing_passwords_key_raises(self, temp_dir: Path) -> None:
        """Test that JSON without 'passwords' key raises error."""
        passwords_file = temp_dir / "passwords.json"
        passwords_file.write_text('{"other_key": []}', encoding="utf-8")

        with pytest.raises(PasswordManagerError, match="corrupt"):
            PasswordManager(data_dir=temp_dir)


class TestRemoveByIndex:
    """Test cases for remove_by_index method."""

    def test_remove_by_index_success(self, manager: PasswordManager) -> None:
        """Test removing password by valid index."""
        manager.add_password("first")
        manager.add_password("second")
        manager.add_password("third")

        removed = manager.remove_by_index(1)  # 0-based, removes "second"

        assert removed == "second"
        assert manager.get_passwords() == ["first", "third"]
        assert manager.count() == 2

    def test_remove_by_index_first(self, manager: PasswordManager) -> None:
        """Test removing first password by index."""
        manager.add_password("first")
        manager.add_password("second")

        removed = manager.remove_by_index(0)

        assert removed == "first"
        assert "first" not in manager.get_passwords()

    def test_remove_by_index_last(self, manager: PasswordManager) -> None:
        """Test removing last password by index."""
        manager.add_password("first")
        manager.add_password("second")

        removed = manager.remove_by_index(1)

        assert removed == "second"
        assert manager.get_passwords() == ["first"]

    def test_remove_by_index_out_of_range(self, manager: PasswordManager) -> None:
        """Test that invalid index raises error."""
        manager.add_password("only")

        with pytest.raises(PasswordManagerError, match="out of range"):
            manager.remove_by_index(5)

        with pytest.raises(PasswordManagerError, match="out of range"):
            manager.remove_by_index(-1)

    def test_remove_by_index_empty_list(self, manager: PasswordManager) -> None:
        """Test removing from empty list."""
        with pytest.raises(PasswordManagerError, match="out of range"):
            manager.remove_by_index(0)

    def test_remove_by_index_persistence(self, manager: PasswordManager) -> None:
        """Test that remove_by_index saves to file."""
        manager.add_password("test")

        manager.remove_by_index(0)

        # Create new instance to verify persistence
        manager2 = PasswordManager(data_dir=manager.data_dir)
        assert "test" not in manager2.get_passwords()


class TestEdgeCases:
    """Test edge cases for PasswordManager."""

    def test_add_empty_string_password(self, manager: PasswordManager) -> None:
        """Test adding empty string password now raises validation error."""
        with pytest.raises(PasswordValidationError, match="cannot be empty"):
            manager.add_password("")

    def test_add_whitespace_only_password(self, manager: PasswordManager) -> None:
        """Test adding whitespace-only password now raises validation error."""
        with pytest.raises(PasswordValidationError, match="whitespace-only"):
            manager.add_password("   ")

    def test_add_very_long_password(self, manager: PasswordManager) -> None:
        """Test adding very long password now raises validation error."""
        long_pwd = "a" * 10001
        with pytest.raises(PasswordValidationError, match="exceeds maximum length"):
            manager.add_password(long_pwd)

    def test_concurrent_access_simulation(self, temp_dir: Path) -> None:
        """Simulate concurrent access by multiple manager instances."""
        manager1 = PasswordManager(data_dir=temp_dir)
        manager1.add_password("password1")

        manager2 = PasswordManager(data_dir=temp_dir)
        manager2.add_password("password2")

        # Verify persistence via a fresh instance
        manager3 = PasswordManager(data_dir=temp_dir)
        passwords = manager3.get_passwords()
        assert "password1" in passwords
        assert "password2" in passwords

    def test_permission_error_on_load(self, temp_dir: Path) -> None:
        """Test handling permission error when loading passwords file."""
        passwords_file = temp_dir / "passwords.json"
        passwords_file.write_text('{"passwords": ["test"]}')

        with patch("pathlib.Path.read_text", side_effect=PermissionError("Access denied")):
            with pytest.raises(PasswordManagerError):
                PasswordManager(data_dir=temp_dir)

    def test_permission_error_on_save(self, manager: PasswordManager) -> None:
        """Test handling permission error when saving passwords."""
        with patch("pathlib.Path.write_text", side_effect=PermissionError("Access denied")):
            with pytest.raises(PermissionError):
                manager.add_password("new_password")


class TestPasswordManagerWithValidator:
    """Test cases for PasswordManager with custom validators."""

    def test_add_password_with_custom_validator(
        self, manager: PasswordManager
    ) -> None:
        """Test adding password with custom validator."""
        from try7z.utils import PasswordValidationError, PasswordValidator

        class MinLengthValidator(PasswordValidator):
            def __init__(self, min_length: int = 5):
                self.min_length = min_length

            def validate(self, password: str) -> None:
                if len(password) < self.min_length:
                    raise PasswordValidationError(
                        f"Password must be at least {self.min_length} characters"
                    )

        # Short password should fail with custom validator
        with pytest.raises(PasswordValidationError, match="at least 5"):
            manager.add_password("abc", validator=MinLengthValidator())

        # Valid password should pass
        manager.add_password("abcdef", validator=MinLengthValidator())
        assert "abcdef" in manager.get_passwords()

    def test_add_password_default_uses_basic_validator(
        self, manager: PasswordManager
    ) -> None:
        """Test that default validator is BasicPasswordValidator."""
        # Empty string should be rejected by default
        with pytest.raises(PasswordValidationError, match="cannot be empty"):
            manager.add_password("")


class TestBatchMode:
    """Test cases for batch/auto_save mode."""

    def test_auto_save_true_writes_immediately(self, temp_dir: Path) -> None:
        """Test that auto_save=True writes to disk immediately."""
        pm = PasswordManager(data_dir=temp_dir, auto_save=True)
        pm.add_password("immediate")

        # Verify by reading file directly
        data = json.loads(pm.passwords_file.read_text(encoding="utf-8"))
        assert "immediate" in data["passwords"]

    def test_auto_save_false_defers_writes(self, temp_dir: Path) -> None:
        """Test that auto_save=False does not write until save() called."""
        # Create initial file so we can verify it wasn't modified
        passwords_file = temp_dir / "passwords.json"
        passwords_file.write_text('{"passwords": ["existing"]}', encoding="utf-8")

        pm = PasswordManager(data_dir=temp_dir, auto_save=False)
        pm.add_password("deferred")

        # File should still only have the original password
        data = json.loads(pm.passwords_file.read_text(encoding="utf-8"))
        assert "deferred" not in data["passwords"]
        assert pm._dirty is True

        pm.save()
        data = json.loads(pm.passwords_file.read_text(encoding="utf-8"))
        assert "deferred" in data["passwords"]
        assert pm._dirty is False

    def test_save_only_when_dirty(self, temp_dir: Path) -> None:
        """Test that save() only writes when dirty."""
        pm = PasswordManager(data_dir=temp_dir, auto_save=False)

        # save() with no changes should not raise and should be no-op
        pm.save()
        assert pm._dirty is False

    def test_context_manager_auto_saves_on_exit(self, temp_dir: Path) -> None:
        """Test that context manager saves on successful exit."""
        passwords_file = temp_dir / "passwords.json"
        passwords_file.write_text('{"passwords": []}', encoding="utf-8")

        with PasswordManager(data_dir=temp_dir, auto_save=True) as pm:
            pm.add_password("ctx1")
            pm.add_password("ctx2")
            # Inside context, auto_save is False
            data = json.loads(pm.passwords_file.read_text(encoding="utf-8"))
            assert "ctx1" not in data["passwords"]

        # After exit, should be saved
        data = json.loads(pm.passwords_file.read_text(encoding="utf-8"))
        assert "ctx1" in data["passwords"]
        assert "ctx2" in data["passwords"]

    def test_context_manager_no_save_on_exception(self, temp_dir: Path) -> None:
        """Test that context manager does not save if exception occurs."""
        passwords_file = temp_dir / "passwords.json"
        passwords_file.write_text('{"passwords": []}', encoding="utf-8")

        try:
            with PasswordManager(data_dir=temp_dir, auto_save=True) as pm:
                pm.add_password("should_not_persist")
                raise ValueError(" intentional error")
        except ValueError:
            pass

        # Password should not have been saved
        data = json.loads(pm.passwords_file.read_text(encoding="utf-8"))
        assert "should_not_persist" not in data["passwords"]

    def test_batch_remove_and_clear(self, temp_dir: Path) -> None:
        """Test batch remove and clear operations."""
        pm = PasswordManager(data_dir=temp_dir, auto_save=False)
        pm.add_password("p1")
        pm.add_password("p2")
        pm.add_password("p3")
        pm.save()

        # Batch remove
        with PasswordManager(data_dir=temp_dir, auto_save=True) as pm2:
            pm2.remove_password("p1")
            pm2.remove_by_index(0)  # removes "p2" after p1 removed

        passwords = pm2.get_passwords()
        assert passwords == ["p3"]

        # Batch clear
        with PasswordManager(data_dir=temp_dir, auto_save=True) as pm3:
            pm3.clear_passwords()

        assert pm3.count() == 0
        data = json.loads(pm3.passwords_file.read_text(encoding="utf-8"))
        assert data["passwords"] == []

    def test_reentrance_restores_auto_save(self, temp_dir: Path) -> None:
        """Test that auto_save state is restored after context manager."""
        pm = PasswordManager(data_dir=temp_dir, auto_save=True)
        with pm:
            assert pm._auto_save is False
        assert pm._auto_save is True
