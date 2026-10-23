"""Bounded static extractors. No specimen import, eval, or execution."""
import ast
import io
import json
from pathlib import Path
import sys
import tokenize
import tomllib
from .common import ScanError, canonical, digest, identity, sha, strict_json
from .symbols import annotate

MAX_RECORDS = 12000
PACKAGE = Path(__file__).resolve().parent


def adapter_revision(family):
    parts = [sha(Path(__file__).read_bytes()), sha((PACKAGE / "symbols.py").read_bytes()),
             sys.version.split()[0], family]
    if family == "anchor":
        from ..anchor_language import verify_source_pins, source_directory
        verify_source_pins()
        parts.extend([sha((PACKAGE / "anchor_adapter.py").read_bytes()),
                      sha((source_directory() / "tools/anchor_structure.py").read_bytes()),
                      sha((source_directory() / "SOURCE-PINS.json").read_bytes())])
    if family == "typescript":
        parts.append(sha((PACKAGE / "javascript.py").read_bytes()))
    if family == "interface":
        parts.append(sha((PACKAGE / "interfaces.py").read_bytes()))
    if family == "pe":
        parts.append(sha((PACKAGE / "pe.py").read_bytes()))
    return digest(parts)


def dotted(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted(node.value)
        return prefix + "." + node.attr if prefix else node.attr
    return "<dynamic>"


class Builder:
    def __init__(self, path, source_hash, *, module_line=1, module_end_line=1):
        self.path, self.source_hash = path, source_hash
        self.nodes, self.edges = [], []
        self.module = self.add("module", path, module_line, module_end_line, None, 0)

    def add(self, kind, name, line, end, owner, depth, *, syntax_sha256=None,
            relocation_sha256=None, signature_sha256=None, **attrs):
        if len(self.nodes) >= MAX_RECORDS:
            raise ScanError("Per-file record budget exceeded")
        nid = identity("node", self.path, self.source_hash, kind, line, len(self.nodes))
        self.nodes.append({"id": nid, "kind": kind, "name": str(name)[:300], "path": self.path,
                           "name_truncated": len(str(name)) > 300,
                           "line": line, "end_line": end, "owner": owner, "loop_depth": depth,
                           "source_sha256": self.source_hash, "evidence": "STATIC_SYNTAX", "attributes": attrs,
                           "syntax_sha256": syntax_sha256 or (self.source_hash if kind == "module" else digest([kind, name, attrs])),
                           "relocation_sha256": relocation_sha256 or (self.source_hash if kind == "module" else digest([kind, attrs])),
                           "signature_sha256": signature_sha256})
        if owner:
            self.edges.append({"id": identity("edge", owner, nid, "contains"), "src": owner, "dst": nid,
                               "kind": "contains", "evidence": "STATIC_SYNTAX"})
        return nid

    def result(self, family, gaps=None):
        annotate(self.nodes)
        return {"family": family, "nodes": self.nodes, "edges": self.edges, "gaps": gaps or [],
                "coverage": "STRUCTURE_AND_PARTIAL_FLOW" if family in ("python", "typescript") else "STRUCTURE_ONLY"}


class PythonExtractor(ast.NodeVisitor):
    def __init__(self, path, data):
        encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
        self.text = data.decode(encoding)
        self.tree = ast.parse(self.text, filename=path, type_comments=True)
        if sum(1 for _ in ast.walk(self.tree)) > 60000:
            raise ScanError("Python AST node budget exceeded")
        self.b = Builder(path, sha(data))
        self.fingerprint_bytes = 0
        module_syntax = self.fingerprint(self.tree)
        self.b.nodes[0].update(syntax_sha256=module_syntax, relocation_sha256=module_syntax)
        self.owner, self.depth, self.loops, self.shadows = self.b.module, 0, [], set()

    def add(self, kind, name, node, **attrs):
        syntax = self.fingerprint(node)
        relocation = syntax
        signature = None
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            values = {field: getattr(node, field) for field in node._fields}
            values["name"] = "<declaration>"
            relocation = self.fingerprint(type(node)(**values))
            signature_fields = ("args", "returns", "decorator_list", "type_params") if hasattr(node, "args") else ("bases", "keywords", "decorator_list", "type_params")
            signature = digest([type(node).__name__, [(field, ast.dump(value, include_attributes=False) if isinstance(value, ast.AST)
                                else [ast.dump(item, include_attributes=False) for item in value] if isinstance(value, list)
                                else value) for field in signature_fields if (value := getattr(node, field, None)) is not None]])
        result = self.b.add(kind, name, getattr(node, "lineno", 1), getattr(node, "end_lineno", 1), self.owner, self.depth,
                            syntax_sha256=syntax, relocation_sha256=relocation, signature_sha256=signature, **attrs)
        for loop in self.loops:
            if len(self.b.edges) >= MAX_RECORDS * 4:
                raise ScanError("Per-file relationship budget exceeded")
            self.b.edges.append({"id": identity("edge", loop, result, "inside_loop"), "src": loop, "dst": result,
                                 "kind": "inside_loop", "evidence": "STATIC_SYNTAX"})
        return result

    def fingerprint(self, node):
        text = ast.dump(node, include_attributes=False)
        self.fingerprint_bytes += len(text)
        if len(text) > 2_000_000 or self.fingerprint_bytes > 16_000_000:
            raise ScanError("Python comparison fingerprint budget exceeded")
        return sha(text.encode("utf-8"))

    def visit_FunctionDef(self, node):
        fn = self.add("function", node.name, node, async_function=isinstance(node, ast.AsyncFunctionDef))
        # Defaults and decorators belong to definition-time context, not invocation body.
        for child in [*node.decorator_list, *node.args.defaults, *[v for v in node.args.kw_defaults if v is not None]]:
            self.visit(child)
        previous = self.owner, self.depth, self.loops, self.shadows
        args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        shadows = {arg.arg for arg in args}
        if node.args.vararg: shadows.add(node.args.vararg.arg)
        if node.args.kwarg: shadows.add(node.args.kwarg.arg)
        pending = list(node.body)
        while pending:
            child = pending.pop()
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                shadows.add(child.name)
                continue
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                shadows.add(child.id)
            if isinstance(child, (ast.Import, ast.ImportFrom)):
                shadows.update(a.asname or a.name.split(".")[0] for a in child.names)
            pending.extend(ast.iter_child_nodes(child))
        self.owner, self.depth, self.loops, self.shadows = fn, 0, [], shadows | self.shadows
        for child in node.body: self.visit(child)
        self.owner, self.depth, self.loops, self.shadows = previous

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node):
        fn = self.add("function", "<lambda>", node)
        for child in [*node.args.defaults, *[v for v in node.args.kw_defaults if v is not None]]: self.visit(child)
        previous = self.owner, self.depth, self.loops, self.shadows
        self.owner, self.depth, self.loops = fn, 0, []
        self.shadows = self.shadows | {a.arg for a in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]}
        self.visit(node.body)
        self.owner, self.depth, self.loops, self.shadows = previous

    def visit_ClassDef(self, node):
        cls = self.add("class", node.name, node)
        for child in [*node.bases, *node.decorator_list]: self.visit(child)
        owner = self.owner
        self.owner = cls
        for child in node.body: self.visit(child)
        self.owner = owner

    def visit_Call(self, node):
        callee = dotted(node.func)
        try:
            expression = ast.unparse(node)[:500]
        except RecursionError:
            expression = callee
        self.add("call", callee, node, expression=expression, shadowed=callee in self.shadows,
                 target_resolution="UNRESOLVED", positional_args=len(node.args))
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.add("import", alias.name, node, level=0, module=alias.name)

    def visit_ImportFrom(self, node):
        self.add("import", "." * node.level + (node.module or ""), node, level=node.level, module=node.module or "")

    def visit_loop(self, node):
        loop = self.add("loop", type(node).__name__, node, nested_depth=self.depth + 1)
        if isinstance(node, (ast.For, ast.AsyncFor)):
            self.visit(node.iter)  # The outer iterator expression is evaluated once.
        self.depth += 1
        self.loops.append(loop)
        if isinstance(node, ast.While): self.visit(node.test)
        if hasattr(node, "target"): self.visit(node.target)
        for child in node.body: self.visit(child)
        self.loops.pop()
        self.depth -= 1
        for child in node.orelse: self.visit(child)

    def visit_comprehension_expression(self, node):
        loop = self.add("loop", type(node).__name__, node, nested_depth=self.depth + len(node.generators))
        old_depth, old_loops, old_shadows = self.depth, self.loops, self.shadows
        self.loops = list(self.loops)
        self.shadows = set(self.shadows)
        for index, generator in enumerate(node.generators):
            self.visit(generator.iter)
            self.depth += 1
            if index == 0: self.loops.append(loop)
            self.shadows.update(n.id for n in ast.walk(generator.target) if isinstance(n, ast.Name))
            for condition in generator.ifs: self.visit(condition)
        for name in ("elt", "key", "value"):
            if hasattr(node, name): self.visit(getattr(node, name))
        self.depth, self.loops, self.shadows = old_depth, old_loops, old_shadows

    visit_For = visit_AsyncFor = visit_While = visit_loop
    visit_ListComp = visit_SetComp = visit_DictComp = visit_GeneratorExp = visit_comprehension_expression

    def visit_Return(self, node):
        self.add("return", "return", node)
        self.generic_visit(node)

    def visit_Await(self, node):
        self.add("await", "await", node)
        self.generic_visit(node)

    def visit_Try(self, node):
        self.add("try", "try", node, handlers=len(node.handlers), finally_present=bool(node.finalbody))
        self.generic_visit(node)

    visit_TryStar = visit_Try

    def visit_Raise(self, node):
        self.add("raise", "raise", node)
        self.generic_visit(node)

    def visit_With(self, node):
        self.add("with", "resource scope", node)
        self.generic_visit(node)

    visit_AsyncWith = visit_With

    def extract(self):
        self.visit(self.tree)
        return self.b.result("python", ["Static call sites are not runtime counts; attribute/dynamic dispatch is unresolved.",
                                         "No full dataflow, import execution, type inference or behavioral equivalence is claimed."])


def extract(path, data, family, *, deadline=None):
    if family == "python":
        return PythonExtractor(path, data).extract()
    if family == "anchor":
        from .anchor_adapter import extract_anchor
        return extract_anchor(path, data)
    if family == "typescript":
        from .javascript import extract_javascript
        return extract_javascript(path, data, deadline=deadline)
    if family == "pe":
        from .pe import extract_pe
        return extract_pe(path,data,deadline=deadline)
    if family == "interface":
        from .interfaces import extract_interface
        return extract_interface(path, data, deadline=deadline)
    builder = Builder(path, sha(data))
    text = data.decode("utf-8-sig")
    if family == "json":
        value = strict_json(text)
    elif family == "toml":
        value = tomllib.loads(text)
    else:
        raise ScanError("No structure adapter for " + family)
    pending = [("$", value, builder.module)]
    fingerprint_bytes = 0
    while pending:
        key, item, owner = pending.pop()
        representation = canonical(item)
        fingerprint_bytes += len(representation)
        if fingerprint_bytes > 16_000_000:
            raise ScanError("Data comparison fingerprint budget exceeded")
        fingerprint = sha(representation.encode("utf-8"))
        nid = builder.add("data", key, None, None, owner, 0, syntax_sha256=fingerprint,
                          relocation_sha256=fingerprint, value_type=type(item).__name__)
        if isinstance(item, dict):
            pending.extend((str(k), v, nid) for k, v in reversed(list(item.items())))
        elif isinstance(item, list):
            pending.extend((str(i), v, nid) for i, v in reversed(list(enumerate(item))))
    return builder.result(family, ["Data structure only; no executable behavior inferred. Source locations are not available for data fields."])


def typescript_batch(items, node=None, timeout=30):
    raise ScanError("Legacy external batch interface is unavailable; use native extract or the explicitly permitted specialist provider.")
