#!/usr/bin/env python3
"""python -m mantle -- the entry point. See mantle/cli.py."""
import sys

from .cli import main

sys.exit(main() or 0)
