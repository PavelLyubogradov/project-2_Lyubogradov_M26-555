#!/usr/bin/env python3
"""Application entry point."""

from primitive_db.engine import run


def main() -> None:
    """Start the database."""
    run()


if __name__ == "__main__":
    main()
