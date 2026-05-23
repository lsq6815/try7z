"""Archive extraction logic using bundled 7-Zip executable.

This module provides functionality for extracting password-protected archives
using the bundled 7-Zip executable. It supports automatic password attempts
and multiple archive formats.

Supported Formats:
    - .7z (7-Zip archive)
    - .zip (ZIP archive)
    - .rar (RAR archive)

The module locates the bundled 7-Zip binary for the current platform.
Windows x64 is fully supported; Linux and macOS require manual placement
of the 7zz binary in the appropriate lib/ subdirectory.

Example:
    Basic extraction with password list::

        >>> from try7z.extractor import Extractor
        >>> from pathlib import Path
        >>>
        >>> extractor = Extractor(Path("archive.7z"))
        >>> success, password = extractor.try_extract(
        ...     passwords=["pwd1", "pwd2", "pwd3"]
        ... )
        >>> if success:
        ...     print(f"Extracted with password: {password}")
        ...     else:
        ...     print("No password worked")

    Extraction with custom output directory::

        >>> extractor = Extractor(Path("encrypted.zip"))
        >>> success, pwd = extractor.extract_with_passwords(
        ...     passwords=["secret123"],
        ...     output_dir=Path("./extracted")
        ... )
"""

import platform
import re
import shutil
import subprocess
from pathlib import Path

from tqdm import tqdm

from try7z.utils import (
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
        >>> from try7z.extractor import get_7z_path
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
        >>> from try7z.extractor import get_7z_version
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


def _compute_skip_depth(temp_dir: Path) -> int:
    """Count single-child directory levels between root and first branch.

    Walks the extracted temp directory tree using pathlib. The first
    entry in temp_dir is considered the archive root and is always
    kept. Each subsequent level that contains exactly one directory
    (no files, no siblings) increments the skip count. Stops at the
    first level with multiple entries or a file.

    Args:
        temp_dir: Path to the directory containing extracted archive contents.

    Returns:
        Number of single-child directory levels to skip (0 = no flattening).

    Example:
        temp_dir/
          A/           <- root, kept
            B/         <- single child dir -> skip
              C1/      <- multiple entries -> stop
              C2/
        Returns 1 (skip B).
    """
    entries = list(temp_dir.iterdir())
    if len(entries) != 1:
        return 0
    current = entries[0]
    if not current.is_dir():
        return 0

    skip_depth = 0
    while True:
        sub_entries = list(current.iterdir())
        if len(sub_entries) != 1:
            break
        child = sub_entries[0]
        if not child.is_dir():
            break
        skip_depth += 1
        current = child

    return skip_depth


class Extractor:
    """Handle archive extraction with automatic password attempts.

    This class manages the extraction of password-protected archives.
    It validates the archive, attempts extraction with provided passwords,
    and manages output directories.

    Attributes:
        archive_path: Absolute path to the validated archive file.

    Example:
        >>> from pathlib import Path
        >>> from try7z.extractor import Extractor
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
            >>> from try7z.extractor import Extractor
            >>>
            >>> # Valid archive
            >>> extractor = Extractor(Path("document.7z"))
            >>>
            >>> # Invalid path raises error
            >>> Extractor(Path("nonexistent.7z"))
            Traceback (most recent call last):
                ...
            try7z.utils.InvalidArchiveError: Archive not found: ...
        """
        self.archive_path = validate_archive_path(archive_path)

        if not is_supported_archive(self.archive_path):
            raise InvalidArchiveError(f"Unsupported archive format: {self.archive_path.suffix}")

        self._7z_path = get_7z_path()

    def _get_archive_file_count(self) -> int | None:
        """Get the number of files in the archive.

        Uses 7-Zip's list command to count files in the archive.
        This is used for progress bar total calculation.

        Returns:
            Number of files in the archive, or None if count cannot be determined.

        Example:
            >>> from pathlib import Path
            >>> extractor = Extractor(Path("test.7z"))
            >>> count = extractor._get_archive_file_count()
        """
        try:
            result = subprocess.run(
                [str(self._7z_path), "l", str(self.archive_path)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                # Parse the "Files:" line from the output
                for line in result.stdout.split("\n"):
                    if line.strip().startswith("Files:"):
                        match = re.search(r"Files:\s*(\d+)", line)
                        if match:
                            return int(match.group(1))
        except Exception:
            pass
        return None

    def _try_passwords(
        self,
        output_dir: Path,
        passwords_to_try: list[str | None],
        show_password_progress: bool = False,
    ) -> tuple[bool, str | None, int]:
        """Try extracting with each password until one works.

        Iterates through the password list, attempting extraction with
        each one. Returns immediately on first success.

        Args:
            output_dir: Directory to extract files to.
            passwords_to_try: List of passwords to try (None for no password).
            show_password_progress: Whether to display progress messages.

        Returns:
            Tuple of (success, used_password, attempts_count):
            - success: True if a password worked
            - used_password: The password that worked, or None
            - attempts_count: Number of passwords tried before success
                             (or total count if none worked)

        Raises:
            ExtractionError: If extraction fails for non-password reasons.
        """
        for i, password in enumerate(passwords_to_try):
            if show_password_progress:
                print(
                    f"\rTrying password {i + 1}/{len(passwords_to_try)}...",
                    end="",
                    flush=True,
                )

            try:
                if self._extract_with_password(output_dir, password, show_progress=False):
                    return True, password, i + 1
            except ExtractionError:
                raise
            except Exception:
                continue

        return False, None, len(passwords_to_try)

    def try_extract(
        self,
        output_dir: Path | None = None,
        passwords: list[str] | None = None,
        show_progress: bool = False,
        show_password_progress: bool = False,
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
            show_progress: Whether to display a progress bar during extraction.
                          Only shown when a correct password is found.
            show_password_progress: Whether to display which password is being
                                   tried. Shows "Trying password X/N..." and
                                   refreshes on the same line.

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
            >>> from try7z.extractor import Extractor
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

        passwords_to_try: list[str | None] = list(passwords) if passwords else [None]

        success = False
        used_password = None

        try:
            if show_progress:
                # Two-phase extraction with progress bar:
                # Phase 1: Find correct password without showing progress
                found_success, correct_password, attempts = self._try_passwords(
                    output_dir, passwords_to_try, show_password_progress
                )

                # Phase 2: If found and progress requested, re-extract with progress
                if found_success:
                    if show_password_progress:
                        print(f"\nFound after {attempts} trie(s)!")

                    # Remove the output dir to re-extract cleanly
                    if output_dir.exists():
                        shutil.rmtree(output_dir)
                    output_dir.mkdir(parents=True, exist_ok=True)

                    success = self._extract_with_password(
                        output_dir, correct_password, show_progress=True
                    )
                    if success:
                        used_password = correct_password
                        return True, correct_password
                else:
                    # No password worked - move to new line
                    if show_password_progress:
                        print()
            else:
                # Original behavior: try passwords without progress bar
                success, used_password, _ = self._try_passwords(
                    output_dir, passwords_to_try, show_password_progress
                )
                if success:
                    return True, used_password
        finally:
            if not success and created_by_us and output_dir.exists():
                try:
                    if not any(output_dir.iterdir()):
                        output_dir.rmdir()
                except OSError:
                    pass

        return success, used_password

    def _extract_with_password(
        self,
        output_dir: Path,
        password: str | None,
        show_progress: bool = False,
    ) -> bool:
        """Extract archive with a specific password.

        Internal method that executes 7-Zip with the given password.
        Parses the output to determine if extraction succeeded or if
        the password was incorrect.

        Args:
            output_dir: Directory to extract files to.
            password: Password to use, or None for no password.
            show_progress: Whether to display a progress bar during extraction.

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

        if not show_progress:
            # Fast mode without progress bar
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

            except subprocess.TimeoutExpired as e:
                raise ExtractionError("Extraction timed out") from e
            except FileNotFoundError as e:
                raise ExtractionError(f"7-Zip executable not found: {self._7z_path}") from e
        else:
            # Progress bar mode
            return self._extract_with_progress(cmd)

    def _extract_with_progress(self, cmd: list[str]) -> bool:
        """Extract archive with progress bar display.

        Uses 7-Zip's -bsp1 flag to output progress information,
        which is parsed in real-time to update a tqdm progress bar.

        7-Zip uses \\r (carriage return) to refresh progress on the same line,
        so this method handles raw byte output to properly capture progress.

        The progress bar is only displayed when actual extraction progress
        is detected (progress increases from 0% to higher values).

        Args:
            cmd: 7-Zip command list (will add -bsp1 flag).

        Returns:
            True if extraction succeeded, False if password was incorrect.

        Raises:
            ExtractionError: If extraction fails for non-password reasons.
        """
        # Add -bsp1 to send progress to stdout
        cmd_with_progress = [*cmd, "-bsp1"]

        # Regex to match 7-Zip progress: " 10%"
        progress_pattern = re.compile(r"^\s*(\d+)%")

        # Get total file count for the progress bar
        total_files = self._get_archive_file_count()

        pbar = None
        progress_detected = False
        max_percent = 0
        try:
            process = subprocess.Popen(
                cmd_with_progress,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
            )

            # Read raw bytes to handle \\r properly
            full_output = b""
            current_line = b""

            if process.stdout is not None:
                while True:
                    byte = process.stdout.read(1)
                    if not byte:
                        break

                    full_output += byte

                    if byte == b"\r":
                        # Carriage return - current line is refreshed
                        line_str = current_line.decode("utf-8", errors="replace")

                        # Check for progress pattern (e.g., " 10%")
                        match = progress_pattern.match(line_str)
                        if match:
                            percent = int(match.group(1))

                            # Track max percent to detect real progress
                            if percent > max_percent:
                                max_percent = percent
                                progress_detected = True

                            # Only create progress bar if we've seen real progress
                            # (progress > 0 or we've been processing for a while)
                            if progress_detected and pbar is None:
                                pbar = tqdm(
                                    total=100,
                                    desc="Extracting",
                                    unit="%",
                                    ncols=80,
                                    bar_format="{desc}: {percentage:3.0f}%|{bar}| "
                                              "{n_fmt}/{total_fmt}",
                                )

                            # Update progress bar if it exists
                            if pbar is not None:
                                pbar.n = percent
                                if total_files is not None:
                                    pbar.set_postfix(count=f"{percent}% of {total_files} files")
                                pbar.update(0)  # Refresh display

                        # Reset current line (\\r means overwrite)
                        current_line = b""
                    elif byte == b"\n":
                        # New line - keep the line for later analysis
                        current_line = b""
                    else:
                        current_line += byte

            # Wait for process to complete and get stderr
            _, stderr_bytes = process.communicate(timeout=300)
            stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""

            # Close progress bar only if extraction succeeded
            # If failed (wrong password), clear the partial progress display
            if pbar is not None:
                if process.returncode == 0:
                    pbar.close()
                else:
                    # Clear the progress bar line for failed extractions
                    pbar.clear()
                    pbar.close()

            # Decode full output for error analysis
            full_output_str = full_output.decode("utf-8", errors="replace")

            # Determine result
            if process.returncode == 0:
                return True

            # Check for password error
            all_output = (full_output_str + stderr).lower()
            if "wrong password" in all_output or "password" in all_output:
                return False

            raise ExtractionError(f"Extraction failed: {stderr or full_output_str[-500:]}")

        except subprocess.TimeoutExpired as e:
            if pbar is not None:
                pbar.clear()
                pbar.close()
            raise ExtractionError("Extraction timed out") from e
        except FileNotFoundError as e:
            if pbar is not None:
                pbar.clear()
                pbar.close()
            raise ExtractionError(f"7-Zip executable not found: {self._7z_path}") from e

    def extract_with_passwords(
        self,
        passwords: list[str],
        output_dir: Path | None = None,
        show_progress: bool = False,
        show_password_progress: bool = False,
    ) -> tuple[bool, str | None]:
        """Extract archive trying multiple passwords, raising on failure.

        Similar to try_extract(), but raises PasswordNotFoundError if
        none of the provided passwords work. This is useful when you
        want to distinguish between "no password worked" and other errors.

        Args:
            passwords: List of passwords to try. Must not be empty.
            output_dir: Directory to extract to. If None, creates a
                       subdirectory named after the archive.
            show_progress: Whether to display a progress bar during extraction.
            show_password_progress: Whether to display which password is being
                                   tried. Shows "Trying password X/N..." and
                                   refreshes on the same line.

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
            >>> from try7z.extractor import Extractor
            >>> from try7z.utils import PasswordNotFoundError
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
        success, used_password = self.try_extract(
            output_dir, passwords, show_progress, show_password_progress
        )

        if not success:
            raise PasswordNotFoundError(f"No matching password found for {self.archive_path.name}")

        return success, used_password
