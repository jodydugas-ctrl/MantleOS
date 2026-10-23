"""Repo-relative filesystem locations, resolved once from this file's position.

The `mantle` package lives at ``<repo>/src/mantle``; data that is *not* part of the
importable package (example AppAIs, eggs, the documents tree, the README the doctor reads)
lives at the repo root. Modules that need those locations import them from here instead of
recomputing ``os.path.dirname`` chains, so a layout change touches one file, not many.
"""
from __future__ import annotations

import os

# <repo>/src/mantle/paths.py -> SRC_DIR=<repo>/src, REPO_ROOT=<repo>
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(SRC_DIR)

EXAMPLES_DIR = os.path.join(REPO_ROOT, "examples")
EGGS_DIR = os.path.join(EXAMPLES_DIR, "eggs")
SAMPLE_APP_DIR = os.path.join(EXAMPLES_DIR, "sample_app")
DOCUMENTS_DIR = os.path.join(REPO_ROOT, "documents")
README_PATH = os.path.join(REPO_ROOT, "README.md")
