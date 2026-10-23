#!/usr/bin/env python3
"""App-level Mantle certification for Organize.AppAI.

Runs `mantle certify` on the resident nest but scoped to application
invariants only. The mantle-os repository-invariants (SPORE-2, FRICTION-1,
GHNEST-13, GHNEST-17, ...) assert properties of the mantle-os *source*
repository (e.g. docs/MANTLE2_CONSOLIDATION_MATRIX.md, src/mantle/nest,
spore lifecycle receipts, audit workflow templates). Those files live in the
mantle-os repo, not in this application repo, so they must not gate an
application's certificate.

Usage: python scripts/certify_app.py <nest> --out=FILE
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mantle.certify import CertificationError, certify_nest, write_certificate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nest", help="path to the Mantle nest to certify")
    parser.add_argument("--out", default=None, help="write the certificate here")
    args = parser.parse_args(argv)

    nest = str(Path(args.nest).resolve(strict=True))
    try:
        receipt = certify_nest(nest, include_invariants=False)
    except CertificationError as error:
        print(f"CERTIFICATION BLOCKED: {error}", file=sys.stderr)
        return 1

    if args.out:
        path = write_certificate(receipt, args.out)
        print(f"Certificate written to {path}")
    else:
        print(f"Certification hashed: {receipt['receipt']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
