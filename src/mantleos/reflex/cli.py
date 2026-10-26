"""Compatibility command; the maintained CLI lives in reflex_book."""
from ..reflex_book.cli import main

if __name__ == '__main__':
    raise SystemExit(main())
