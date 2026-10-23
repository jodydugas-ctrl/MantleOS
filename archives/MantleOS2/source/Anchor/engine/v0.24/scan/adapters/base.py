from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..inventory import FileRecord
from ..model import ExtractionResult


class Adapter(ABC):
    name = "base"
    version = "1"

    def cache_version(self, root: Path, record: FileRecord) -> str:
        """Return the cache-context version for this file.

        Most adapters depend only on their implementation version plus source bytes. Compiler-backed
        adapters may override this to include parse-context fingerprints such as compile_commands flags.
        """
        return str(self.version)

    @abstractmethod
    def accepts(self, record: FileRecord) -> bool:
        raise NotImplementedError

    @abstractmethod
    def extract(self, root: Path, record: FileRecord, text: str) -> ExtractionResult:
        raise NotImplementedError
