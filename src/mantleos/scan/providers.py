"""Versioned optional capabilities and a strict syntax-only provider boundary."""
import base64
import copy
from pathlib import Path, PurePosixPath
import re
import tempfile
from .adapters import Builder
from .common import ScanError, canonical, digest, outside, read_json, sha, strict_json

PACKAGE = Path(__file__).resolve().parent


def run(*args, **kwargs):
    """Load the optional host transport only after explicit provider invocation."""
    from .provider_process import run as transport
    return transport(*args, **kwargs)
HEX = re.compile(r"[a-f0-9]{64}\Z")
CATALOG = {
    "schema": "scan.provider-catalog/1",
    "providers": [
        {"id": "typescript-static", "contract": "scan.syntax-provider/1", "enabled_by_default": False,
         "families": ["typescript"], "hosts": ["Windows", "Linux", "Darwin"],
         "evidence_classes": ["STATIC_SYNTAX"], "executes_specimen": False,
         "requires": ["explicit policy", "per-invocation external permission", "pinned Node and TypeScript"],
         "limitations": ["Parser only; no type checker, import execution, emit or runtime counts.",
                         "Specialist enhancement to native JS/TS coverage; native records are retained unchanged.",
                         "Trusted host process; no OS sandbox or enforced network denial."]},
    ]
}


def fields(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        raise ScanError("Invalid provider contract fields")


def relative(value):
    if not isinstance(value, str) or not value or len(value) > 1000 or "\\" in value or ":" in value or "\x00" in value:
        raise ScanError("Invalid relative source path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in (".", "..", "") for part in value.split("/")):
        raise ScanError("Invalid relative source path")
    return value


def pinned_file(record, limit, source):
    fields(record, ("path", "sha256"))
    if not isinstance(record["path"], str) or not isinstance(record["sha256"], str) or not HEX.fullmatch(record["sha256"]):
        raise ScanError("Provider file pin is malformed")
    raw = Path(record["path"])
    if not raw.is_absolute() or raw.is_symlink() or raw.resolve() != raw.absolute():
        raise ScanError("Provider paths must be absolute and must not redirect")
    path = raw.resolve()
    outside(path, source)
    if not path.is_file() or path.stat().st_size > limit:
        raise ScanError("Provider is missing or exceeds its file budget")
    with path.open("rb") as stream: data = stream.read(limit + 1)
    if len(data) > limit or sha(data) != record["sha256"]:
        raise ScanError("Provider file pin mismatch")
    return path, data


class Providers:
    def __init__(self, policy=None, *, allow_external=False, source):
        self.config, self.revision, self.error = None, "disabled", None
        self.source = source
        if type(allow_external) is not bool:
            raise ScanError("External provider permission must be boolean")
        if not allow_external:
            self.error = "Optional JS/TS provider disabled; external permission was not supplied"
            return
        if policy is None:
            self.error = "Optional JS/TS provider disabled; no policy supplied"
            return
        try:
            outside(policy, source)
            document = read_json(policy, limit=64_000)
            fields(document, ("schema", "providers"))
            if document["schema"] != "scan.provider-policy/1" or not isinstance(document["providers"], dict):
                raise ScanError("Unsupported provider policy")
            if document["providers"].keys() - {"typescript-static"}:
                raise ScanError("Provider has no admitted implementation")
            config = document["providers"].get("typescript-static", {"enabled": False})
            if not isinstance(config, dict) or type(config.get("enabled")) is not bool:
                raise ScanError("Provider enabled flag must be boolean")
            if not config["enabled"]:
                fields(config, ("enabled",))
                self.error = "Optional JS/TS provider disabled by policy"
                return
            fields(config, ("enabled", "version", "node", "library", "package"))
            if not isinstance(config["version"], str) or not re.fullmatch(r"\d+\.\d+\.\d+", config["version"]):
                raise ScanError("An exact TypeScript version is required")
            node, _ = pinned_file(config["node"], 150_000_000, source)
            library, _ = pinned_file(config["library"], 30_000_000, source)
            package, metadata = pinned_file(config["package"], 64_000, source)
            info = strict_json(metadata.decode("utf-8"))
            if info.get("name") != "typescript" or info.get("version") != config["version"]:
                raise ScanError("TypeScript package identity mismatch")
            if library != package.parent / "lib" / "typescript.js":
                raise ScanError("Only the pinned standalone TypeScript compiler module is admitted")
            self.config = dict(config, node_path=str(node), library_path=str(library))
            self.revision = digest([document, sha((PACKAGE / "typescript_bridge.cjs").read_bytes()),
                                    sha(Path(__file__).read_bytes()), sha((PACKAGE / "provider_process.py").read_bytes())])
        except (OSError, ValueError, TypeError, RecursionError) as error:
            self.error = "Optional JS/TS provider unavailable: " + str(error)[:400]

    def extract(self, path, data, *, timeout=30):
        if self.config is None: raise ScanError(self.error)
        relative(path)
        if len(data) > 2_000_000: raise ScanError("Provider source byte budget exceeded")
        config = self.config
        # Check again before each launch, not only before cache lookup. These are
        # point-in-time pins, not an atomic lock against a hostile local operator.
        for key, limit in (("node", 150_000_000), ("library", 30_000_000), ("package", 64_000)):
            pinned_file(config[key], limit, self.source)
        request = {"schema": "scan.syntax-request/1", "path": path, "source_sha256": sha(data),
                   "source_base64": base64.b64encode(data).decode("ascii"), "version": config["version"]}
        with tempfile.TemporaryDirectory(prefix="mantle-syntax-") as cwd:
            raw = run([config["node_path"], "--max-old-space-size=256", str(PACKAGE / "typescript_bridge.cjs"),
                       config["library_path"]], canonical(request).encode(), cwd=cwd, timeout=timeout)
        value = strict_json(raw.decode("utf-8"))
        result = syntax_result(value, path, data, config["version"])
        result["provider"] = {"id": "typescript-static", "version": config["version"], "revision": self.revision}
        return result


def enhance(native, specialist):
    """Keep native records verbatim; namespace additional specialist structure."""
    from .common import identity
    result = copy.deepcopy(native)
    native_nodes = result["nodes"]
    native_by_id = {node["id"]: node for node in native_nodes}
    def key(node, owners):
        parent = owners.get(node["owner"])
        scope = parent.get("comparison", {}).get("logical_scope", []) if parent else []
        return digest([node["kind"], node["name"], node["line"], node["end_line"], scope])
    candidates = {}
    for node in native_nodes: candidates.setdefault(key(node,native_by_id), []).append(node)
    original = {node["id"]:node for node in specialist["nodes"]}
    provider = specialist["provider"]
    mapped, additions = {}, []
    for ordinal,node in enumerate(specialist["nodes"]):
        if node["kind"] == "module":
            mapped[node["id"]] = native_nodes[0]["id"]; continue
        matches = candidates.get(key(node,original), [])
        if len(matches) == 1:
            mapped[node["id"]] = matches[0]["id"]; continue
        value = copy.deepcopy(node)
        value["id"] = identity("node-provider",provider,node["id"])
        mapped[node["id"]] = value["id"]
        value["owner"] = mapped[node["owner"]]
        value["attributes"].update(analysis_origin="optional-provider",provider=copy.deepcopy(provider),provider_record_ordinal=ordinal)
        value["symbol_key"] = "symbol:" + digest([provider,value["symbol_key"]])
        value["comparison"]["logical_key"] = "logical:" + digest([provider,value["comparison"]["logical_key"]])
        additions.append(value)
    if len(native_nodes) + len(additions) > 12000: raise ScanError("Specialist enhancement record budget exceeded")
    native_nodes.extend(additions)
    existing = {(edge["src"],edge["dst"],edge["kind"]) for edge in result["edges"]}
    for edge in specialist["edges"]:
        source, target = mapped[edge["src"]], mapped[edge["dst"]]
        if (source,target,edge["kind"]) in existing: continue
        value = copy.deepcopy(edge)
        value.update(id=identity("edge-provider",provider,edge["id"]),src=source,dst=target,analysis_origin="optional-provider")
        result["edges"].append(value); existing.add((source,target,edge["kind"]))
    result["provider"] = copy.deepcopy(provider)
    result["enhancement_coverage"] = specialist["coverage"]
    result["gaps"] = list(native["gaps"]) + list(specialist["gaps"])
    return result


def syntax_result(value, path, data, version):
    fields(value, ("schema", "path", "source_sha256", "version", "records"))
    if (value["schema"], value["path"], value["source_sha256"], value["version"]) != ("scan.syntax-provider/1", path, sha(data), version):
        raise ScanError("Provider source/schema identity mismatch")
    records = value["records"]
    if not isinstance(records, list) or not 1 <= len(records) <= 12000:
        raise ScanError("Provider record budget exceeded")
    lines = len(data.decode("utf-8-sig").splitlines()) + 1
    builder = Builder(path, sha(data))
    ids, loop_depths = {}, {}
    kinds = {"module", "function", "class", "import", "call", "loop", "return", "await", "try", "raise"}
    for index, record in enumerate(records):
        fields(record, ("id", "kind", "name", "line", "end_line", "owner", "loop_depth", "attributes",
                       "syntax_sha256", "relocation_sha256", "signature_sha256"))
        if type(record["id"]) is not int or record["id"] != index or not isinstance(record["kind"], str) or record["kind"] not in kinds:
            raise ScanError("Invalid provider syntax identity or kind")
        if not isinstance(record["name"], str) or len(record["name"]) > 1000:
            raise ScanError("Invalid provider name")
        if any(type(record[key]) is not int for key in ("line", "end_line", "loop_depth")) or not 1 <= record["line"] <= record["end_line"] <= lines:
            raise ScanError("Provider source span is out of range")
        if not 0 <= record["loop_depth"] <= 512:
            raise ScanError("Invalid provider loop depth")
        for key in ("syntax_sha256", "relocation_sha256", "signature_sha256"):
            if key == "signature_sha256" and record[key] is None: continue
            if not isinstance(record[key], str) or not HEX.fullmatch(record[key]):
                raise ScanError("Invalid syntax fingerprint")
        attrs = record["attributes"]
        expected = {"module": (), "function": ("async",), "class": (), "import": ("module",),
                    "call": ("shadowed",), "loop": ("loop_type",), "return": (), "await": (), "try": (), "raise": ()}
        fields(attrs, expected[record["kind"]])
        if record["kind"] == "function" and type(attrs["async"]) is not bool:
            raise ScanError("Invalid function attributes")
        if record["kind"] == "call" and attrs["shadowed"] is not True:
            raise ScanError("External parser cannot establish an unshadowed runtime binding")
        if record["kind"] == "import":
            if not isinstance(attrs["module"], str) or len(attrs["module"]) > 1000:
                raise ScanError("Invalid import module")
        if record["kind"] == "loop" and attrs["loop_type"] not in ("for", "for_in", "for_of", "while", "do"):
            raise ScanError("Invalid loop type")
        owner = record["owner"]
        if index == 0:
            if record["kind"] != "module" or record["name"] != path or owner is not None or record["loop_depth"] != 0:
                raise ScanError("Provider must return exactly one root module")
            builder.nodes[0].update(line=record["line"], end_line=record["end_line"], syntax_sha256=record["syntax_sha256"],
                                    relocation_sha256=record["relocation_sha256"])
            nid = builder.module
        else:
            if record["kind"] == "module" or type(owner) is not int or owner not in ids:
                raise ScanError("Provider owner must precede its child")
            parent = records[owner]
            if not parent["line"] <= record["line"] <= record["end_line"] <= parent["end_line"]:
                raise ScanError("Provider child span escapes its owner")
            depth = loop_depths[owner] + int(parent["kind"] == "loop")
            if parent["kind"] in ("function", "class"): depth = 0
            if record["loop_depth"] != depth:
                raise ScanError("Provider loop depth contradicts containment")
            nid = builder.add(record["kind"], record["name"], record["line"], record["end_line"], ids[owner], depth,
                              syntax_sha256=record["syntax_sha256"], relocation_sha256=record["relocation_sha256"],
                              signature_sha256=record["signature_sha256"], **attrs)
        ids[index], loop_depths[index] = nid, record["loop_depth"]
    return builder.result("typescript", ["Optional TypeScript parser syntax only; calls remain unresolved.",
                                         "Provider output is untrusted observation data; source hash binding is not proof of semantic correctness.",
                                         "No import execution, type inference, runtime observation or OS sandbox is claimed."])
