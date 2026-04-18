"""Entry point for running autopasstryunzip as a module.

This module allows the package to be executed using Python's -m flag::

    python -m autopasstryunzip [command] [options]

This is equivalent to running the ``autopass-unzip`` CLI command after
installation. All commands and options are identical.

Example:
    Show help::

        $ python -m autopasstryunzip --help

    Add a password::

        $ python -m autopasstryunzip add "mypassword"

    Extract an archive::

        $ python -m autopasstryunzip extract archive.7z

Note:
    This module simply calls :func:`autopasstryunzip.main.main`.
    See :mod:`autopasstryunzip.main` for the full CLI documentation.
"""

import sys

from autopasstryunzip.main import main

if __name__ == "__main__":
    sys.exit(main())
