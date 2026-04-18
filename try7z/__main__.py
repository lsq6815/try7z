"""Entry point for running try7z as a module.

This module allows the package to be executed using Python's -m flag::

    python -m try7z [command] [options]

This is equivalent to running the ``try7z`` CLI command after
installation. All commands and options are identical.

Example:
    Show help::

        $ python -m try7z --help

    Add a password::

        $ python -m try7z add "mypassword"

    Extract an archive::

        $ python -m try7z extract archive.7z

Note:
    This module simply calls :func:`try7z.main.main`.
    See :mod:`try7z.main` for the full CLI documentation.
"""

import sys

from try7z.main import main

if __name__ == "__main__":
    sys.exit(main())
