"""Archive extraction logic using bundled 7-Zip executable.

This module provides functionality for extracting password-protected archives
using the bundled 7-Zip executable. It supports automatic password attempts
and multiple archive formats.

Supported Formats:
    - .7z (7-Zip archive)
    - .zip (ZIP archive)
    - .rar (RAR archive)

The module automatically locates the appropriate 7-Zip binary for the
current platform (Windows x64, Linux x64, macOS x64).

Example:
    Basic extraction with password list::

        >>> from autopasstryunzip.extractor import Extractor
        >>> from pathlib import Path
        >>>
        >>> extractor = Extractor(Path("archive.7z"))
        >>> success, password = extractor.try_extract(
        ...     passwords=["pwd1", "pwd2", "pwd3"]
        ... )
        >>> if success:
        ...     print(f"Extracted with password: {password}")
        ... else:
        ...     print("No password worked")

    Extraction with custom output directory::

        >>> extractor = Extractor(Path("encrypted.zip"))
        >>> success, pwd = extractor.extract_with_passwords(
        ...     passwords=["secret123"],
        ...     output_dir=Path("./extracted")
        ... )
"""

import platform
import subprocess
from pathlib import Path

from autopasstryunzip.utils import (
    ExtractionError,
    InvalidArchiveError,
    PasswordNotFoundError,
    get_package_root,
    is_supported_archive,
    validate_archive_path,
)


def get_7z_path() -> Path:
    """Get path to the bundled 7z executable.

    Returns the path to the appropriate 7-Zip binary for the current
    platform and architecture. The executable is bundled with the package
    in the lib/ directory.

    Returns:
        Path to 7z.exe (Windows) or 7zz (Linux/macOS).

    Raises:
        ExtractionError: If the current platform or architecture is not supported.

    Example:
        >>> from autopasstryunzip.extractor import get_7z_path
        >>> path = get_7z_path()
        >>> print(path.name)
        '7z.exe'  # On Windows
    """
    package_root = get_package_root()

    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "windows":
        if machine in ("amd64", "x86_64"):
            return package_root / "lib" / "win-x64" / "7z.exe"
    elif system == "linux":
        if machine in ("amd64", "x86_64"):
            return package_root / "lib" / "linux-x64" / "7zz"
    elif system == "darwin":
        return package_root / "lib" / "mac-x64" / "7zz"

    raise ExtractionError(f"Unsupported platform: {system} {machine}")


def get_7z_version() -> str:
    """Get 7-Zip version string.

    Executes 7-Zip with the -version flag and extracts the version
    information from the output.

    Returns:
        Version string from 7-Zip (first line of output).
        Example: "7-Zip (r) 26.00 (x86) : Igor Pavlov : Public domain : 2026-02-12"
        Returns "unknown" if version cannot be determined.

    Example:
        >>> from autopasstryunzip.extractor import get_7z_version
        >>> version = get_7z_version()
        >>> print(version)
        7-Zip (r) 26.00 (x86) : Igor Pavlov : Public domain : 2026-02-12
    """
    try:
        result = subprocess.run(
            [str(get_7z_path()), "-version"],
            capture_output=True,
            text=True,
        )
        # First line contains version info
        return result.stdout.strip().split("\n")[0]
    except Exception:
        return "unknown"


class Extractor:
    """Handle archive extraction with automatic password attempts.

    This class manages the extraction of password-protected archives.
    It validates the archive, attempts extraction with provided passwords,
    and manages output directories.

    Attributes:
        archive_path: Absolute path to the validated archive file.

    Example:
        >>> from pathlib import Path
        >>> from autopasstryunzip.extractor import Extractor
        >>>
        >>> # Create extractor (validates archive)
        >>> extractor = Extractor(Path("my_archive.7z"))
        >>>
        >>> # Try extraction with passwords
        >>> passwords = ["password1", "password2"]
        >>> success, used_password = extractor.try_extract(passwords=passwords)
        >>>
        >>> if success:
        ...     print(f"Extracted with: {used_password}")

    Note:
        The archive is validated during initialization. Invalid or
        unsupported archives will raise InvalidArchiveError immediately.
    """

    def __init__(self, archive_path: Path) -> None:
        """Initialize extractor with archive path.

        Validates the archive path and checks that the file format
        is supported. Stores the absolute path for extraction.

        Args:
            archive_path: Path to the archive file (relative or absolute).

        Raises:
            InvalidArchiveError: If archive doesn't exist, isn't a file,
                                or has an unsupported format.

        Example:
            >>> from pathlib import Path
            >>> from autopasstryunzip.extractor import Extractor
            >>>
            >>> # Valid archive
            >>> extractor = Extractor(Path("document.7z"))
            >>>
            >>> # Invalid path raises error
            >>> Extractor(Path("nonexistent.7z"))
            Traceback (most recent call last):
                ...
            autopasstryunzip.utils.InvalidArchiveError: Archive not found: ...
        """
        self.archive_path = validate_archive_path(archive_path)

        if not is_supported_archive(self.archive_path):
            raise InvalidArchiveError(f"Unsupported archive format: {self.archive_path.suffix}")

        self._7z_path = get_7z_path()

    def try_extract(
        self,
        output_dir: Path | None = None,
        passwords: list[str] | None = None,
    ) -> tuple[bool, str | None]:
        """Attempt to extract archive with given passwords.

        Tries to extract the archive using each password in the list
        sequentially. If no password is needed, extraction succeeds
        with the first attempt (password=None).

        Args:
            output_dir: Directory to extract files to. If None, creates
                       a subdirectory named after the archive in the
                       archive's parent directory.
            passwords: List of passwords to try. If None or empty,
                      attempts extraction without a password.

        Returns:
            Tuple of (success, used_password):
            - success: True if extraction succeeded
            - used_password: The password that worked, or None if no
                            password was needed or extraction failed

        Raises:
            ExtractionError: If extraction fails for non-password reasons
                           (e.g., corrupted archive, missing 7-Zip).

        Example:
            >>> from pathlib import Path
            >>> from autopasstryunzip.extractor import Extractor
            >>>
            >>> extractor = Extractor(Path("encrypted.7z"))
            >>>
            >>> # Try with password list
            >>> success, pwd = extractor.try_extract(
            ...     passwords=["wrong", "correct", "another"]
            ... )
            >>> if success:
            ...     print(f"Password was: {pwd}")  # "correct"
            >>>
            >>> # Try without password (for unencrypted archives)
            >>> extractor2 = Extractor(Path("plain.zip"))
            >>> success, pwd = extractor2.try_extract()
            >>> print(pwd)  # None (no password needed)
        """
        if output_dir is None:
            output_dir = self.archive_path.parent / self.archive_path.stem

        output_dir = output_dir.resolve()
        created_by_us = not output_dir.exists()
        output_dir.mkdir(parents=True, exist_ok=True)

        passwords_to_try: list[str | None]
        if passwords:
            passwords_to_try = list(passwords)
        else:
            passwords_to_try = [None]

        success = False
        used_password = None

        try:
            for password in passwords_to_try:
                try:
                    success = self._extract_with_password(output_dir, password)
                    if success:
                        used_password = password
                        return True, password
                except ExtractionError:
                    raise
                except Exception:
                    continue
        finally:
            if not success and created_by_us and output_dir.exists():
                try:
                    if not any(output_dir.iterdir()):
                        output_dir.rmdir()
                except OSError:
                    pass

        return success, used_password

    def _extract_with_password(self, output_dir: Path, password: str | None) -> bool:
        """Extract archive with a specific password.

        Internal method that executes 7-Zip with the given password.
        Parses the output to determine if extraction succeeded or if
        the password was incorrect.

        Args:
            output_dir: Directory to extract files to.
            password: Password to use, or None for no password.

        Returns:
            True if extraction succeeded, False if password was incorrect.

        Raises:
            ExtractionError: If extraction fails for non-password reasons
                           (e.g., timeout, missing executable, corrupted data).

        Note:
            This is an internal method. Use try_extract() or
            extract_with_passwords() for normal operations.
        """
        cmd = [str(self._7z_path), "x", "-y", f"-o{output_dir}", str(self.archive_path)]

        if password:
            cmd.insert(3, f"-p{password}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                return True

            error_output = result.stderr.lower() + result.stdout.lower()

            if "wrong password" in error_output or "password" in error_output:
                return False

            raise ExtractionError(f"Extraction failed: {result.stderr or result.stdout}")

        except subprocess.TimeoutExpired:
            raise ExtractionError("Extraction timed out")
        except FileNotFoundError:
            raise ExtractionError(f"7-Zip executable not found: {self._7z_path}")

    def extract_with_passwords(
        self,
        passwords: list[str],
        output_dir: Path | None = None,
    ) -> tuple[bool, str | None]:
        """Extract archive trying multiple passwords, raising on failure.

        Similar to try_extract(), but raises PasswordNotFoundError if
        none of the provided passwords work. This is useful when you
        want to distinguish between "no password worked" and other errors.

        Args:
            passwords: List of passwords to try. Must not be empty.
            output_dir: Directory to extract to. If None, creates a
                       subdirectory named after the archive.

        Returns:
            Tuple of (success, used_password). Success is always True
            when this method returns normally (non-exception).

        Raises:
            PasswordNotFoundError: If no password in the list successfully
                                  decrypts the archive.
            ExtractionError: If extraction fails for other reasons
                           (e.g., corrupted archive, timeout).

        Example:
            >>> from pathlib import Path
            >>> from autopasstryunzip.extractor import Extractor
            >>> from autopasstryunzip.utils import PasswordNotFoundError
            >>>
            >>> extractor = Extractor(Path("secret.7z"))
            >>>
            >>> try:
            ...     success, pwd = extractor.extract_with_passwords(
            ...         passwords=["guess1", "guess2"]
            ...     )
            ...     print(f"Success with: {pwd}")
            ... except PasswordNotFoundError:
            ...     print("Password not in list")
        """
        success, used_password = self.try_extract(output_dir, passwords)

        if not success and passwords:
            raise PasswordNotFoundError(f"No matching password found for {self.archive_path.name}")

        return success, used_password
