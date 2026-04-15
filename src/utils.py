"""Custom exceptions and helper functions for the application."""

from pathlib import Path


class AutoPassError(Exception):
    """Base exception for AutoPassTryUnzip application."""

    pass


class PasswordManagerError(AutoPassError):
    """Exception raised for password manager errors."""

    pass


class ExtractionError(AutoPassError):
    """Exception raised for extraction errors."""

    pass


class InvalidArchiveError(ExtractionError):
    """Exception raised when archive is invalid or corrupted."""

    pass


class PasswordNotFoundError(ExtractionError):
    """Exception raised when no matching password is found."""

    pass


def validate_archive_path(archive_path: Path) -> Path:
    """Validate that the archive path exists and is a file.

    Args:
        archive_path: Path to the archive file.

    Returns:
        Validated absolute path.

    Raises:
        InvalidArchiveError: If path doesn't exist or isn't a file.
    """
    archive_path = archive_path.resolve()

    if not archive_path.exists():
        raise InvalidArchiveError(f"Archive not found: {archive_path}")

    if not archive_path.is_file():
        raise InvalidArchiveError(f"Path is not a file: {archive_path}")

    return archive_path


def get_supported_extensions() -> set[str]:
    """Return set of supported archive extensions.

    Returns:
        Set of supported file extensions (lowercase, with dot).
    """
    return {".7z", ".zip", ".rar"}


def is_supported_archive(file_path: Path) -> bool:
    """Check if file has a supported archive extension.

    Args:
        file_path: Path to check.

    Returns:
        True if extension is supported.
    """
    return file_path.suffix.lower() in get_supported_extensions()
