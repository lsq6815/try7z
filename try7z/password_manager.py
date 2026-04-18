"""Password storage and management for try7z.

This module provides the PasswordManager class for managing a list of
passwords stored in a plain text JSON file. Passwords are stored in the
user's data directory and persist across application restarts.

Storage Format:
    Passwords are stored in a JSON file with the following structure::

        {
          "passwords": [
            "password1",
            "password2",
            "password3"
          ]
        }

    The storage location is platform-specific (see get_user_data_dir).

Security Note:
    Passwords are stored in PLAIN TEXT. This is intentional for ease of
    user access and editing, but means the passwords file should be
    treated as sensitive data.

Example:
    Basic usage::

        >>> from try7z.password_manager import PasswordManager
        >>>
        >>> # Create manager (loads existing passwords automatically)
        >>> pm = PasswordManager()
        >>>
        >>> # Add passwords
        >>> pm.add_password("secret123")
        >>> pm.add_password("mypassword")
        >>>
        >>> # List passwords
        >>> passwords = pm.get_passwords()
        >>> print(passwords)
        ['secret123', 'mypassword']
        >>>
        >>> # Remove by value
        >>> pm.remove_password("secret123")
        >>>
        >>> # Remove by index
        >>> pm.remove_by_index(0)  # Removes "mypassword"
        >>>
        >>> # Clear all
        >>> pm.clear_passwords()
"""

import json
from pathlib import Path

from try7z.utils import PasswordManagerError, get_user_data_dir


class PasswordManager:
    """Manage password storage in plain text JSON file.

    This class provides methods to add, remove, and retrieve passwords
    from a persistent JSON file. Passwords are stored in the user's
    data directory and automatically loaded on initialization.

    Attributes:
        data_dir: Directory where passwords.json is stored.
        passwords_file: Full path to the passwords.json file.

    Example:
        >>> from try7z.password_manager import PasswordManager
        >>> import tempfile
        >>>
        >>> # Create with custom data directory (for testing)
        >>> with tempfile.TemporaryDirectory() as tmpdir:
        ...     pm = PasswordManager(data_dir=Path(tmpdir))
        ...     pm.add_password("test123")
        ...     print(pm.count())
        1
        ...     print(pm.get_passwords())
        ['test123']
    """

    def __init__(self, data_dir: Path | None = None) -> None:
        """Initialize the password manager.

        Creates the data directory if it doesn't exist and loads
        existing passwords from the passwords.json file.

        Args:
            data_dir: Directory for storing passwords. If None, uses
                     the platform-specific user data directory.

        Example:
            >>> # Use default location
            >>> pm = PasswordManager()
            >>>
            >>> # Use custom location
            >>> pm = PasswordManager(data_dir=Path("/path/to/dir"))
        """
        self.data_dir = data_dir or get_user_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.passwords_file = self.data_dir / "passwords.json"
        self._passwords: list[str] = []

        self._load_passwords()

    def _load_passwords(self) -> None:
        """Load passwords from the JSON file.

        Internal method called during initialization. If the file
        doesn't exist or is invalid, starts with an empty list.
        """
        if self.passwords_file.exists():
            try:
                data = json.loads(self.passwords_file.read_text(encoding="utf-8"))
                self._passwords = data.get("passwords", [])
            except (json.JSONDecodeError, KeyError):
                self._passwords = []
        else:
            self._passwords = []

    def _save_passwords(self) -> None:
        """Save passwords to the JSON file.

        Internal method called after any modification to persist
        changes to disk.
        """
        data = {"passwords": self._passwords}
        self.passwords_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def add_password(self, password: str) -> None:
        """Add a password to the list.

        Adds a new password to the stored list and saves to disk.
        Duplicate passwords are not allowed.

        Args:
            password: The password string to add.

        Raises:
            PasswordManagerError: If the password already exists in the list.

        Example:
            >>> pm = PasswordManager()
            >>> pm.add_password("mysecret")
            >>> pm.count()
            1
            >>> pm.add_password("mysecret")  # Raises error
            Traceback (most recent call last):
                ...
            try7z.utils.PasswordManagerError: Password already exists
        """
        if password in self._passwords:
            raise PasswordManagerError("Password already exists")

        self._passwords.append(password)
        self._save_passwords()

    def remove_password(self, password: str) -> None:
        """Remove a password from the list by value.

        Removes the first occurrence of the specified password and
        saves changes to disk.

        Args:
            password: The password string to remove.

        Raises:
            PasswordManagerError: If the password doesn't exist in the list.

        Example:
            >>> pm = PasswordManager()
            >>> pm.add_password("test123")
            >>> pm.remove_password("test123")
            >>> pm.count()
            0
            >>> pm.remove_password("nonexistent")  # Raises error
            Traceback (most recent call last):
                ...
            try7z.utils.PasswordManagerError: Password not found
        """
        if password not in self._passwords:
            raise PasswordManagerError("Password not found")

        self._passwords.remove(password)
        self._save_passwords()

    def get_passwords(self) -> list[str]:
        """Get a copy of all stored passwords.

        Returns a shallow copy of the password list to prevent
        external modifications from affecting the internal state.

        Returns:
            List of stored password strings.

        Example:
            >>> pm = PasswordManager()
            >>> pm.add_password("pwd1")
            >>> pm.add_password("pwd2")
            >>> passwords = pm.get_passwords()
            >>> passwords
            ['pwd1', 'pwd2']
            >>> passwords.append("pwd3")  # Doesn't affect internal list
            >>> pm.count()
            2
        """
        return self._passwords.copy()

    def clear_passwords(self) -> None:
        """Remove all stored passwords.

        Clears the entire password list and saves the empty list
        to disk. This operation cannot be undone.

        Example:
            >>> pm = PasswordManager()
            >>> pm.add_password("pwd1")
            >>> pm.add_password("pwd2")
            >>> pm.clear_passwords()
            >>> pm.count()
            0
            >>> pm.get_passwords()
            []
        """
        self._passwords = []
        self._save_passwords()

    def count(self) -> int:
        """Get the number of stored passwords.

        Returns:
            Number of passwords currently stored.

        Example:
            >>> pm = PasswordManager()
            >>> pm.count()
            0
            >>> pm.add_password("test")
            >>> pm.count()
            1
        """
        return len(self._passwords)

    def remove_by_index(self, index: int) -> str:
        """Remove a password by its index in the list.

        Removes the password at the specified 0-based index and
        returns the removed password.

        Args:
            index: 0-based index to remove (0 = first password).

        Returns:
            The removed password string.

        Raises:
            PasswordManagerError: If index is out of range (negative or
                                 greater than or equal to count).

        Example:
            >>> pm = PasswordManager()
            >>> pm.add_password("first")
            >>> pm.add_password("second")
            >>> pm.add_password("third")
            >>> pm.remove_by_index(1)  # Removes "second"
            'second'
            >>> pm.get_passwords()
            ['first', 'third']
            >>> pm.remove_by_index(5)  # Raises error
            Traceback (most recent call last):
                ...
            try7z.utils.PasswordManagerError: Index 6 out of range
        """
        if not 0 <= index < len(self._passwords):
            raise PasswordManagerError(f"Index {index + 1} out of range")

        removed = self._passwords.pop(index)
        self._save_passwords()
        return removed
