"""Entry point for running try7z CLI as a module.

This module allows the CLI to be executed using Python's -m flag::

    python -m try7z.cli [command] [options]

This is equivalent to running the ``try7z`` CLI command after
installation. All commands and options are identical.

Example:
    Show help::

        $ python -m try7z.cli --help

    Add a password::

        $ python -m try7z.cli add "mypassword"

    Extract an archive::

        $ python -m try7z.cli extract archive.7z

Note:
    This module calls :func:`try7z.cli.main`.
    See :mod:`try7z.cli.main` for the full CLI documentation.
"""

import sys

from try7z.cli import main

if __name__ == "__main__":
    sys.exit(main())
