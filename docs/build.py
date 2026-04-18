"""Build Sphinx documentation using pure Python.

This script provides a cross-platform way to build documentation
without requiring ``make`` to be installed.
"""

import sys
from pathlib import Path

from sphinx.cmd.build import main as sphinx_build


def build() -> int:
    """Build HTML documentation.

    Returns:
        int: Exit code from Sphinx build (0 for success).
    """
    docs_dir = Path(__file__).parent.resolve()
    build_dir = docs_dir / "_build" / "html"
    build_dir.mkdir(parents=True, exist_ok=True)

    return sphinx_build([
        "-b", "html",
        str(docs_dir),
        str(build_dir),
    ])


if __name__ == "__main__":
    sys.exit(build())
