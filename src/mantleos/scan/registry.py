"""One adapter per syntax family; extensions and lens variants reuse implementations."""
from pathlib import Path
import re
from .common import ScanError, digest, read_json, write_json

DEFAULTS = {".py": "python", ".pyi": "python", ".pyw": "python",
            ".js": "typescript", ".jsx": "typescript", ".ts": "typescript",
            ".tsx": "typescript", ".mjs": "typescript", ".cjs": "typescript",
            ".mts": "typescript", ".cts": "typescript",
            ".ui": "interface", ".html": "interface", ".htm": "interface",
            ".json": "json", ".toml": "toml", ".anchor": "anchor",
            ".dll":"pe", ".exe":"pe", ".sys":"pe", ".winmd":"pe", ".netmodule":"pe"}
FAMILIES = {"python", "typescript", "json", "toml", "anchor", "pe", "interface"}
FILTERS = ('code', 'interface', 'data')


def select_filters(value):
    if value is None:
        return list(FILTERS)
    if not isinstance(value, (list, tuple)) or not value or any(v not in FILTERS for v in value):
        raise ScanError('Use existing scan filters: code, interface, data')
    return [name for name in FILTERS if name in value]


def source_filter(family):
    return 'interface' if family == 'interface' else 'data' if family in ('json', 'toml') else 'code'


LENSES = {
    "anchor": {"description": "Static Molecule ownership and serialized Anchor slots; no runtime routing", "kinds": ["anchor_molecule", "anchor"], "min_loop_depth": 0},
    "organic": {"description": "Responsibilities and ownership candidates", "kinds": ["module", "function", "class", "import"], "min_loop_depth": 0},
    "plumbing": {"description": "Static routes, repetition and feedback; not measured liquid flow", "kinds": ["module", "function", "call", "loop", "return", "await"], "min_loop_depth": 0},
    "lifetime": {"description": "Calls inside repetition; preparation and reuse hypotheses", "kinds": ["call", "loop"], "min_loop_depth": 1},
    "reliability": {"description": "Exception handling, raising and resource scopes", "kinds": ["try", "raise", "with", "await"], "min_loop_depth": 0},
    "structure": {"description": "All observed syntax records", "kinds": [], "min_loop_depth": 0},
}
ALIASES = {"anatomy": "organic", "biological": "organic", "pipes": "plumbing", "flow": "plumbing", "reuse": "lifetime"}


class Registry:
    def __init__(self, workspace):
        self.workspace = Path(workspace)
        self.path = self.workspace / "registry.json"
        self.data = read_json(self.path) if self.path.exists() else {"schema": "scan.registry/1", "extensions": {}, "lenses": {}}
        if self.data.get("schema") != "scan.registry/1":
            raise ScanError("Unsupported registry")
        for ext, family in self.data["extensions"].items():
            self.check_extension(ext, family)
        for name, spec in self.data["lenses"].items():
            if not re.fullmatch(r"[a-z][a-z0-9_-]{0,47}", name) or spec.get("base") not in LENSES:
                raise ScanError("Invalid lens variant")
            if not isinstance(spec.get("kinds"), list) or not all(isinstance(k, str) for k in spec["kinds"]):
                raise ScanError("Invalid lens kinds")
            if type(spec.get("min_loop_depth")) is not int or spec["min_loop_depth"] < 0:
                raise ScanError("Invalid lens depth")

    @staticmethod
    def check_extension(ext, family):
        if not re.fullmatch(r"\.[a-z0-9_]{1,16}", ext) or family not in FAMILIES:
            raise ScanError("Use a lowercase extension and an existing adapter family")
        if ext in DEFAULTS and DEFAULTS[ext] != family:
            raise ScanError("Cannot reassign a built-in extension to different syntax")

    def family(self, path):
        ext = Path(path).suffix.lower()
        return self.data["extensions"].get(ext, DEFAULTS.get(ext, "inventory"))

    def map_extension(self, ext, family):
        self.check_extension(ext, family)
        self.data["extensions"][ext] = family
        write_json(self.path, self.data)

    def lenses(self):
        result = {name: {**spec, "base": name} for name, spec in LENSES.items()}
        result.update(self.data["lenses"])
        return result

    def lens(self, name):
        name = ALIASES.get(name, name)
        if name not in self.lenses():
            raise ScanError("Unknown lens; list existing lenses before making a variant")
        return self.lenses()[name]

    def variant(self, name, base, kinds=None, min_loop_depth=None):
        base = ALIASES.get(base, base)
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,47}", name) or name in self.lenses() or name in ALIASES:
            raise ScanError("Choose a new simple lens name")
        original = self.lens(base)
        spec = {"base": original["base"], "description": "Configured view of " + base,
                "kinds": original["kinds"] if kinds is None else kinds,
                "min_loop_depth": original["min_loop_depth"] if min_loop_depth is None else min_loop_depth}
        if type(spec["min_loop_depth"]) is not int or spec["min_loop_depth"] < 0:
            raise ScanError("Invalid loop depth")
        # An equivalent filter already does the job: reuse it rather than proliferate names.
        for existing, value in self.lenses().items():
            if set(value["kinds"]) == set(spec["kinds"]) and value["min_loop_depth"] == spec["min_loop_depth"]:
                return {"name": existing, "created": False, "reason": "Equivalent existing filter reused"}
        self.data["lenses"][name] = spec
        write_json(self.path, self.data)
        return {"name": name, "created": True, "base": spec["base"]}
