"""CLI package for try7z.

This package provides the command-line interface for managing passwords
and extracting archives.

Example:
    Import the CLI entry point::

        >>> from try7z.cli import main
        >>> # main()  # Would start the CLI

    Run as a module::

        $ python -m try7z.cli
"""

from try7z.cli.main import main

__all__ = ["main"]
