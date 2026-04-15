"""Tests for PasswordManager."""

import json
import tempfile
from pathlib import Path

import pytest

from src.password_manager import PasswordManager
from src.utils import PasswordManagerError


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
