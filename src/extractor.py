"""Archive extraction logic using py7zr."""

from pathlib import Path

import py7zr

from src.utils import (
    ExtractionError,
    InvalidArchiveError,
    PasswordNotFoundError,
    is_supported_archive,
    validate_archive_path,
)


class Extractor:
    """Handle archive extraction with automatic password attempts."""

    def __init__(self, archive_path: Path) -> None:
        """Initialize extractor with archive path.

        Args:
            archive_path: Path to the archive file.

        Raises:
            InvalidArchiveError: If archive doesn't exist or isn't supported.
        """
        self.archive_path = validate_archive_path(archive_path)

        if not is_supported_archive(self.archive_path):
            raise InvalidArchiveError(f"Unsupported archive format: {self.archive_path.suffix}")

    def try_extract(
        self,
        output_dir: Path | None = None,
        passwords: list[str] | None = None,
    ) -> tuple[bool, str | None]:
        """Attempt to extract archive with given passwords.

        Args:
            output_dir: Directory to extract to. Defaults to archive's parent.
            passwords: List of passwords to try. None for no password.

        Returns:
            Tuple of (success, used_password). used_password is None if no
            password was needed or extraction failed.

        Raises:
            ExtractionError: If extraction fails for non-password reasons.
        """
        if output_dir is None:
            output_dir = self.archive_path.parent / self.archive_path.stem

        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        passwords_to_try: list[str | None]
        if passwords:
            passwords_to_try = list(passwords)
        else:
            passwords_to_try = [None]

        for password in passwords_to_try:
            try:
                success = self._extract_with_password(output_dir, password)
                if success:
                    return True, password
            except ExtractionError:
                raise
            except Exception:
                continue

        return False, None

    def _extract_with_password(self, output_dir: Path, password: str | None) -> bool:
        """Extract archive with a specific password.

        Args:
            output_dir: Directory to extract to.
            password: Password to use, or None for no password.

        Returns:
            True if extraction succeeded.

        Raises:
            ExtractionError: If extraction fails for non-password reasons.
        """
        try:
            with py7zr.SevenZipFile(self.archive_path, mode="r", password=password) as archive:
                archive.extractall(path=output_dir)
            return True
        except py7zr.exceptions.PasswordRequired:
            return False
        except py7zr.exceptions.Bad7zFile as e:
            raise InvalidArchiveError(f"Invalid or corrupted archive: {e}")
        except py7zr.exceptions.UnsupportedCompressionMethodError as e:
            raise ExtractionError(f"Unsupported compression method: {e}")
        except Exception as e:
            error_msg = str(e).lower()
            if "password" in error_msg or "decrypt" in error_msg or "corrupt" in error_msg:
                return False
            raise ExtractionError(f"Extraction failed: {e}")

    def extract_with_passwords(
        self,
        passwords: list[str],
        output_dir: Path | None = None,
    ) -> tuple[bool, str | None]:
        """Extract archive trying multiple passwords.

        Args:
            passwords: List of passwords to try.
            output_dir: Directory to extract to.

        Returns:
            Tuple of (success, used_password).

        Raises:
            PasswordNotFoundError: If no password works.
            ExtractionError: If extraction fails for other reasons.
        """
        success, used_password = self.try_extract(output_dir, passwords)

        if not success and passwords:
            raise PasswordNotFoundError(f"No matching password found for {self.archive_path.name}")

        return success, used_password
