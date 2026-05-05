"""try7z - 7-Zip frontend for automatic password extraction.

This package provides tools for managing password lists and automatically
extracting password-protected archives using 7-Zip.

Main Components:
    - PasswordManager: Manage stored passwords in JSON format
    - Extractor: Extract archives with automatic password attempts
    - CLI commands: Command-line interface for all operations

Example:
    Basic usage via command line::

        $ try7z add mypassword
        $ try7z extract archive.7z

    Programmatic usage::

        >>> from try7z.password_manager import PasswordManager
        >>> from try7z.extractor import Extractor
        >>>
        >>> # Manage passwords
        >>> pm = PasswordManager()
        >>> pm.add_password("secret123")
        >>>
        >>> # Extract archive
        >>> extractor = Extractor("archive.7z")
        >>> success, password = extractor.try_extract(passwords=pm.get_passwords())

Attributes:
    __version__: The package version string.
    __build_date__: The build/compilation date.
"""

from datetime import datetime, timezone
from importlib.metadata import version

__version__ = version("try7z")
__build_date__ = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
