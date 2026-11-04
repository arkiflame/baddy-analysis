"""Allows `python -m tactics ...` in addition to the `tactics` console script."""

from tactics.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
