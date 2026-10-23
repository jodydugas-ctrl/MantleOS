"""Deterministic resident foundation for the Hermes Mantle addon."""

from .config import ConfigError, ResidentConfig
from .primer import Primer, build_primer

__all__ = ["ConfigError", "Primer", "ResidentConfig", "build_primer"]
