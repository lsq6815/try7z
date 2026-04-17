"""Archive extraction logic using 7-Zip subprocess."""

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
    """Get path to 7z executable.

    Returns:
        Path to 7z.exe (Windows) or 7zz (Linux/macOS).
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

        self._7z_path = get_7z_path()

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
