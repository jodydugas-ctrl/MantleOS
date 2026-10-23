from .base import Adapter
from .cmake import CMakeAdapter
from .clang_cpp import ClangCppAdapter
from .cpp_qt import CppQtAdapter
from .generic_text import GenericTextAdapter
from .m3c_cpp import M3CCppAdapter
from .qt_ui import QtUiAdapter
from .qt_resource import QtResourceAdapter
from .qmake import QMakeAdapter
from .scintilla_lexilla import ScintillaLexillaAdapter
from .typescript_electron import ElectronMetadataAdapter
from .typescript_electron_final import TypeScriptElectronAdapter

DEFAULT_ADAPTERS = [
    QtUiAdapter(), QtResourceAdapter(), CMakeAdapter(), QMakeAdapter(),
    ClangCppAdapter(), CppQtAdapter(), M3CCppAdapter(), ScintillaLexillaAdapter(),
    TypeScriptElectronAdapter(), ElectronMetadataAdapter(), GenericTextAdapter(),
]

__all__ = [
    "Adapter", "QtUiAdapter", "QtResourceAdapter", "CMakeAdapter", "QMakeAdapter",
    "ClangCppAdapter", "CppQtAdapter", "ScintillaLexillaAdapter", "M3CCppAdapter",
    "TypeScriptElectronAdapter", "ElectronMetadataAdapter", "GenericTextAdapter", "DEFAULT_ADAPTERS",
]
