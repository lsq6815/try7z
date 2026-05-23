"""Custom exceptions and helper functions for the try7z application.

This module provides exception classes for different error scenarios and utility
functions for path management and archive validation.

Exception Hierarchy:

* Try7zError (base)

  * PasswordManagerError
  * PasswordValidationError
  * ExtractionError

    * InvalidArchiveError
    * PasswordNotFoundError

Example:
    Handling different exceptions::

        from try7z.utils import (
            Try7zError,
            PasswordManagerError,
            ExtractionError
        )

        try:
            # Some operation
            pass
        except PasswordManagerError as e:
            print(f"Password error: {e}")
        except ExtractionError as e:
            print(f"Extraction error: {e}")
        except Try7zError as e:
            print(f"General error: {e}")
"""

import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path


class Try7zError(Exception):
    """Base exception for try7z application.

    All custom exceptions in this package inherit from this class.
    Catch this exception to handle any application-specific errors.

    Example:
        >>> try:
        ...     # Some operation
        ...     pass
        ... except Try7zError as e:
        ...     print(f"Application error: {e}")
    """



class PasswordValidationError(Try7zError):
    """Exception raised when password validation fails.

    This exception indicates that a password does not meet
    the required validation criteria.

    Example:
        >>> from try7z.utils import BasicPasswordValidator, PasswordValidationError
        >>> validator = BasicPasswordValidator()
        >>> try:
        ...     validator.validate("")
        ... except PasswordValidationError as e:
        ...     print(e)  # "Password cannot be empty"
    """



class PasswordValidator(ABC):
    """Abstract base class for password validation strategies.

    Implementations define specific validation rules by implementing
    the validate() method.

    Example:
        >>> from try7z.utils import PasswordValidator, PasswordValidationError
        >>> class CustomValidator(PasswordValidator):
        ...     def validate(self, password: str) -> None:
        ...         if len(password) < 5:
        ...             raise PasswordValidationError("Too short")
    """

    @abstractmethod
    def validate(self, password: str) -> None:
        """Validate password against implementation-specific rules.

        Args:
            password: Password string to validate.

        Raises:
            PasswordValidationError: If password fails validation.
        """


class BasicPasswordValidator(PasswordValidator):
    """Basic password validator with common validation rules.

    Validates:
        - Password is not empty
        - Password is not whitespace-only
        - Password does not exceed maximum length

    Attributes:
        MAX_LENGTH: Maximum allowed password length (1000 characters).

    Example:
        >>> from try7z.utils import BasicPasswordValidator, PasswordValidationError
        >>> validator = BasicPasswordValidator()
        >>> validator.validate("valid_password")  # No exception raised
        >>> try:
        ...     validator.validate("")
        ... except PasswordValidationError:
        ...     print("Invalid password")
    """

    MAX_LENGTH = 1000

    def validate(self, password: str) -> None:
        """Validate password against basic rules.

        Args:
            password: Password string to validate.

        Raises:
            PasswordValidationError: If password is empty, whitespace-only,
                or exceeds maximum length.
        """
        if not password:
            raise PasswordValidationError("Password cannot be empty")
        if password.isspace():
            raise PasswordValidationError("Password cannot be whitespace-only")
        if len(password) > self.MAX_LENGTH:
            raise PasswordValidationError(
                f"Password exceeds maximum length of {self.MAX_LENGTH} characters"
            )


class PasswordManagerError(Try7zError):
    """Exception raised for password management errors.

    This exception is raised when password operations fail, such as:
    - Adding a duplicate password
    - Removing a non-existent password
    - Accessing an invalid password index

    Example:
        >>> from try7z.password_manager import PasswordManager
        >>> pm = PasswordManager()
        >>> pm.add_password("test")
        >>> try:
        ...     pm.add_password("test")  # Duplicate
        ... except PasswordManagerError as e:
        ...     print(e)  # "Password already exists"
    """



class ExtractionError(Try7zError):
    """Exception raised for archive extraction errors.

    This exception is raised when archive extraction fails for reasons
    other than incorrect passwords (e.g., corrupted archive, missing
    7-Zip executable, timeout).

    Example:
        >>> from try7z.extractor import Extractor
        >>> try:
        ...     extractor = Extractor("nonexistent.7z")
        ... except ExtractionError as e:
        ...     print(f"Extraction failed: {e}")
    """



class InvalidArchiveError(ExtractionError):
    """Exception raised when archive is invalid, corrupted, or unsupported.

    This exception indicates that the archive file cannot be processed
    due to one of the following reasons:
    - File does not exist
    - Path is not a file
    - File format is not supported (.7z, .zip, .rar only)

    Attributes:
        message: Explanation of why the archive is invalid.

    Example:
        >>> from pathlib import Path
        >>> from try7z.extractor import Extractor
        >>> try:
        ...     extractor = Extractor(Path("document.txt"))  # Not an archive
        ... except InvalidArchiveError as e:
        ...     print(e)  # "Unsupported archive format: .txt"
    """



class PasswordNotFoundError(ExtractionError):
    """Exception raised when no matching password is found for an archive.

    This exception indicates that all provided passwords were tried
    but none successfully decrypted the archive.

    Example:
        >>> from try7z.extractor import Extractor
        >>> extractor = Extractor("encrypted.7z")
        >>> try:
        ...     extractor.extract_with_passwords(["wrong1", "wrong2"])
        ... except PasswordNotFoundError as e:
        ...     print(e)  # "No matching password found for encrypted.7z"
    """



def get_user_data_dir() -> Path:
    """Get the platform-specific user data directory.

    Returns the path to the directory where user-specific data
    (passwords, settings) should be stored. The directory is
    created in the standard location for each operating system.

    Returns:
        Path to the user data directory for storing passwords and settings.
        The directory structure follows platform conventions:

        - Windows: ``%APPDATA%\\try7z``
        - macOS: ``~/Library/Application Support/try7z``
        - Linux: ``~/.local/share/try7z``

    Example:
        >>> from try7z.utils import get_user_data_dir
        >>> data_dir = get_user_data_dir()
        >>> print(data_dir)
        WindowsPath('C:/Users/Username/AppData/Roaming/try7z')

    Note:
        This function returns the path only and does not create the
        directory. Components that use this path (such as PasswordManager)
        are responsible for creating the directory when needed.
    """
    if sys.platform == "win32":
        if app_data := os.environ.get("APPDATA"):
            return Path(app_data) / "try7z"
        return Path.home() / "AppData" / "Roaming" / "try7z"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "try7z"
    return Path.home() / ".local" / "share" / "try7z"


def get_package_root() -> Path:
    """Get the package root directory.

    Returns the absolute path to the try7z package directory.
    This is useful for locating bundled resources like the 7-Zip executable.

    Returns:
        Path to the try7z package directory.

    Example:
        >>> from try7z.utils import get_package_root
        >>> root = get_package_root()
        >>> print(root)
        WindowsPath('C:/.../try7z')
    """
    return Path(__file__).parent


def validate_archive_path(archive_path: Path) -> Path:
    """Validate that the archive path exists and is a file.

    Performs validation checks on the provided archive path:
    1. Resolves to absolute path
    2. Verifies file exists
    3. Verifies path is a file (not a directory)

    Args:
        archive_path: Path to the archive file. Can be relative or absolute.

    Returns:
        Validated absolute path to the archive.

    Raises:
        InvalidArchiveError: If path doesn't exist or isn't a file.

    Example:
        >>> from pathlib import Path
        >>> from try7z.utils import validate_archive_path
        >>> try:
        ...     path = validate_archive_path(Path("archive.7z"))
        ...     print(f"Valid archive: {path}")
        ... except InvalidArchiveError as e:
        ...     print(f"Invalid: {e}")
    """
    archive_path = archive_path.resolve()

    if not archive_path.exists():
        raise InvalidArchiveError(f"Archive not found: {archive_path}")

    if not archive_path.is_file():
        raise InvalidArchiveError(f"Path is not a file: {archive_path}")

    return archive_path


SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".7z", ".zip", ".rar"})
"""Set of supported archive file extensions.

All extensions are lowercase and include the leading dot.
"""


def get_supported_extensions() -> set[str]:
    """Return set of supported archive extensions.

    Returns the file extensions that can be processed by this application.
    All extensions are lowercase and include the leading dot.

    Returns:
        Set of supported file extensions (lowercase, with dot).
        Currently supported: .7z, .zip, .rar

    Example:
        >>> from try7z.utils import get_supported_extensions
        >>> exts = get_supported_extensions()
        >>> print(exts)
        {'.7z', '.zip', '.rar'}
        >>> ".7z" in exts
        True
    """
    return set(SUPPORTED_EXTENSIONS)


def is_supported_archive(file_path: Path) -> bool:
    """Check if file has a supported archive extension.

    Compares the file's extension (case-insensitive) against the list
    of supported archive formats.

    Args:
        file_path: Path to check. The extension is extracted from the
                   filename and compared case-insensitively.

    Returns:
        True if the file extension is supported, False otherwise.

    Example:
        >>> from pathlib import Path
        >>> from try7z.utils import is_supported_archive
        >>> is_supported_archive(Path("document.zip"))
        True
        >>> is_supported_archive(Path("document.ZIP"))  # Case insensitive
        True
        >>> is_supported_archive(Path("document.txt"))
        False
    """
    return file_path.suffix.lower() in SUPPORTED_EXTENSIONS
