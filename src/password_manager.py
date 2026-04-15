"""Password storage and management."""

import json
from pathlib import Path

from src.utils import PasswordManagerError


class PasswordManager:
    """Manage password storage in plain text JSON file."""

    def __init__(self, data_dir: Path | None = None) -> None:
        """Initialize the password manager.

        Args:
            data_dir: Directory for storing passwords.
                     Defaults to 'data/' in project root.
        """
        self.data_dir = data_dir or Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.passwords_file = self.data_dir / "passwords.json"
        self._passwords: list[str] = []

        self._load_passwords()

    def _load_passwords(self) -> None:
        """Load passwords from file."""
        if self.passwords_file.exists():
            try:
                data = json.loads(self.passwords_file.read_text(encoding="utf-8"))
                self._passwords = data.get("passwords", [])
            except (json.JSONDecodeError, KeyError):
                self._passwords = []
        else:
            self._passwords = []

    def _save_passwords(self) -> None:
        """Save passwords to file."""
        data = {"passwords": self._passwords}
        self.passwords_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def add_password(self, password: str) -> None:
        """Add a password to the list.

        Args:
            password: Password to add.

        Raises:
            PasswordManagerError: If password already exists.
        """
        if password in self._passwords:
            raise PasswordManagerError("Password already exists")

        self._passwords.append(password)
        self._save_passwords()

    def remove_password(self, password: str) -> None:
        """Remove a password from the list.

        Args:
            password: Password to remove.

        Raises:
            PasswordManagerError: If password doesn't exist.
        """
        if password not in self._passwords:
            raise PasswordManagerError("Password not found")

        self._passwords.remove(password)
        self._save_passwords()

    def get_passwords(self) -> list[str]:
        """Get list of all stored passwords.

        Returns:
            List of passwords.
        """
        return self._passwords.copy()

    def clear_passwords(self) -> None:
        """Remove all stored passwords."""
        self._passwords = []
        self._save_passwords()

    def count(self) -> int:
        """Get number of stored passwords.

        Returns:
            Number of passwords.
        """
        return len(self._passwords)
