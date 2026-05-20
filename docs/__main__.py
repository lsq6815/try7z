"""Entry point for ``python -m docs``."""

import sys

from docs.build import build

if __name__ == "__main__":
    sys.exit(build())
