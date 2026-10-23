#!/usr/bin/env python3
"""Delete and regenerate the example spore with the current carrier writer."""
from __future__ import annotations

import os
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "src"))

from mantle import spore  # noqa: E402


def main() -> int:
    output = os.path.join(HERE, "example_spore.png")
    if os.path.exists(output):
        os.remove(output)
    spore._demo(output)
    report = spore.verify_spore(output)
    print("%s -> %s" % (os.path.basename(output),
                        "ok" if report["ok"] else report["problems"]))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
