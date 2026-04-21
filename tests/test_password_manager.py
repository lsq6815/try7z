"""Tests for PasswordManager."""

import json
import tempfile
from pathlib import Path

import pytest

from try7z.password_manager import PasswordManager
from try7z.utils import PasswordManagerError


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


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
