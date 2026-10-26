"""Generic Cartridge packing and verification helpers."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import zipfile

from .primer import verify_lock
from .anchor_blueprint import validate_blueprint, render_runner_guide
from .birth import validate_birth
from .systems import validate_systems_contract, interface_index

MANIFEST_SCHEMA = "mantle.manifest/1"

SECRET_EXACT = {".env", "credentials.json", "secrets.json", "service-account.json", "id_rsa", "id_ed25519",
                "oauth-token.bin", "oauth-client.json", "sessions.sqlite", "sessions.sqlite-wal", "sessions.sqlite-shm"}
MAX_ARCHIVE_FILES = 10000
MAX_ARCHIVE_UNCOMPRESSED = 512 * 1024 * 1024


def validate_portable_tree(root: str | Path):
    root = Path(root)
    violations = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if rel.startswith(".git/"):
            continue
        if p.is_symlink():
            violations.append(rel + ":symlink")
            continue
        parts = Path(rel).parts
        if parts and parts[0].lower() in {"nest", ".nest"}:
            violations.append(rel + ":NEST-not-portable")
            continue
        if p.is_file():
            name = p.name.lower()
            if name in SECRET_EXACT or name.startswith(".env."):
                violations.append(rel + ":secret-named-file")
    if violations:
        raise ValueError("Body contains non-portable/secret material: " + ", ".join(violations[:20]))
    return {"schema": "mantle.portable-tree/1", "result": "PASS"}

REQUIRED = [
    "CARTRIDGE.json", "ANATOMY.json", "BIO-SOFTWARE.json", "BIRTH.json", "BODY-STATE.json",
    "SYSTEMS.json", "ANCHOR-CODE.json", "COGNITIVE-SEED.json", "ENGRAM.jsonl",
    "PRIMER/PERSONA.md", "PRIMER/COMMANDMENTS.md", "PRIMER/PRIMER.lock.json",
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def tracked_paths(root: str | Path):
    root = Path(root)
    excluded = {"MANIFEST.json", ".DS_Store"}
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.is_symlink():
            continue
        rel = p.relative_to(root).as_posix()
        if rel in excluded or "/__pycache__/" in "/" + rel + "/" or rel.endswith(".pyc"):
            continue
        if rel.startswith(".git/"):
            continue
        yield p, rel


def write_manifest(root: str | Path) -> dict:
    root = Path(root)
    validate_portable_tree(root)
    files = []
    for p, rel in tracked_paths(root):
        mode = "0755" if os.access(p, os.X_OK) else "0644"
        data = p.read_bytes()
        files.append({"path": rel, "sha256": sha(data), "bytes": len(data), "mode": mode})
    value = {"schema": MANIFEST_SCHEMA, "files": files}
    (root / "MANIFEST.json").write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return value


def verify_manifest(root: str | Path) -> dict:
    root = Path(root)
    validate_portable_tree(root)
    manifest = load_json(root / "MANIFEST.json")
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("Unsupported manifest schema")
    expected = {item["path"]: item for item in manifest.get("files", [])}
    if len(expected) != len(manifest.get("files", [])):
        raise ValueError("Duplicate manifest path")
    actual = {rel: p for p, rel in tracked_paths(root)}
    if set(expected) != set(actual):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        raise ValueError(f"Manifest inventory mismatch missing={missing} extra={extra}")
    for rel, p in actual.items():
        item = expected[rel]
        data = p.read_bytes()
        if sha(data) != item.get("sha256") or len(data) != item.get("bytes"):
            raise ValueError(f"Manifest mismatch: {rel}")
    return manifest


def verify(root: str | Path) -> dict:
    root = Path(root)
    for rel in REQUIRED:
        if not (root / rel).is_file():
            raise ValueError(f"Required Cartridge member missing: {rel}")
    cartridge = load_json(root / "CARTRIDGE.json")
    cell = load_json(root / "ANATOMY.json")
    bio = load_json(root / "BIO-SOFTWARE.json")
    for value, schema in ((cartridge, "mantle.cartridge/1"), (cell, "mantle.anatomy/1"), (bio, "bio-software/3")):
        if value.get("schema") != schema:
            raise ValueError("Unsupported cartridge declaration version: " + str(value.get("schema")))
    birth_value = load_json(root / "BIRTH.json")
    birth = validate_birth(birth_value)
    systems = validate_systems_contract(load_json(root / "SYSTEMS.json"))
    if cartridge.get("kind") != "portable-bio-software-body" or cartridge.get("format") != "vcw/1":
        raise ValueError("Invalid Cartridge Body declaration")
    if cell.get("kind") != "cartridge-anatomy":
        raise ValueError("Invalid cartridge anatomy")
    if cartridge.get("anatomy", {}).get("anatomy_id") != cell.get("anatomy_id"):
        raise ValueError("Cartridge/anatomy identity mismatch")
    if cartridge.get("bio_software", {}).get("id") != bio.get("id") or birth["id"] != bio.get("id"):
        raise ValueError("Cartridge/Birth/Bio-Software identity mismatch")
    birth_decl = cartridge.get("birth", {})
    if birth_decl.get("file") != "BIRTH.json" or birth_decl.get("schema") != "mantle.bio-software-birth/1" or birth_decl.get("sha256") != birth["birth_sha256"]:
        raise ValueError("Cartridge birth contract declaration mismatch")
    if bio.get("birth_contract", {}).get("sha256") != birth["birth_sha256"]:
        raise ValueError("Bio-Software birth contract binding mismatch")
    if bio.get("name") != birth["name"] or bio.get("version") != birth.get("version") or bio.get("kind") != birth["kind"]:
        raise ValueError("Bio-Software fields diverge from BIRTH.json")
    if bio.get("persona", {}).get("name") != birth["primer"]["persona_name"]:
        raise ValueError("Bio-Software Persona name diverges from BIRTH.json")
    expected_persona = birth["primer"]["persona"].strip() + "\n"
    expected_commandments = birth["primer"]["commandments"].strip() + "\n"
    if (root / "PRIMER/PERSONA.md").read_text(encoding="utf-8") != expected_persona:
        raise ValueError("PRIMER/PERSONA.md diverges from BIRTH.json")
    if (root / "PRIMER/COMMANDMENTS.md").read_text(encoding="utf-8") != expected_commandments:
        raise ValueError("PRIMER/COMMANDMENTS.md diverges from BIRTH.json")
    if cartridge.get("distribution") != birth["distribution"]:
        raise ValueError("Cartridge distribution role diverges from BIRTH.json")
    # New Bodies and upgraded packaged agents must carry the refined Anchor Register.
    # Only the current communication contract is admitted.
    from .anchor_language import CAPABILITY, validate_register
    anchor_decl = cell.get('anchor_code', {})
    if anchor_decl.get('schema') == CAPABILITY:
        if anchor_decl.get('file') != 'ANCHOR-CODE.json' or anchor_decl.get('register') != 'ANCHOR-REGISTER.json':
            raise ValueError('Invalid default Anchor Code binding')
        if load_json(root/'ANCHOR-CODE.json').get('schema') != CAPABILITY:
            raise ValueError('Anchor Code declaration mismatch')
        register = validate_register(load_json(root/'ANCHOR-REGISTER.json'))
        if register.get('project') != bio.get('id') or bio.get('default_language') != 'anchor.coding.conversation/1.1':
            raise ValueError('Bio-Application Anchor Coding default mismatch')
    else:
        raise ValueError('Unknown Anchor communication contract')
    interfaces = interface_index(systems)
    portable_bound = {name for name, spec in interfaces.items() if spec.get("binding") == "BOUND"}
    from .organs import system_registry
    system_registry(root).verify_bindings()
    from .engram import read
    read(root/'ENGRAM.jsonl')
    ids = {s.get("id") for s in systems.get("systems", [])}
    required_systems = set(bio.get("required_systems", []))
    if not required_systems <= ids:
        raise ValueError("Required Body system missing")
    blueprint_decl = cartridge.get("anchor_blueprint")
    if blueprint_decl is not None:
        if blueprint_decl.get("file") != "ANCHOR-BLUEPRINT.json" or blueprint_decl.get("schema") != "anchor.blueprint/3":
            raise ValueError("Invalid Anchor Blueprint declaration")
        if not (root / "ANCHOR-BLUEPRINT.json").is_file() or not (root / "RUNNER-GUIDE.md").is_file():
            raise ValueError("Declared Anchor Blueprint or runner guide missing")
        blueprint_value = load_json(root / "ANCHOR-BLUEPRINT.json")
        blueprint = validate_blueprint(blueprint_value, require_ready=True)
        if blueprint_decl.get("sha256") != blueprint["blueprint_sha256"]:
            raise ValueError("Cartridge Anchor Blueprint digest mismatch")
        if (root / "RUNNER-GUIDE.md").read_text(encoding="utf-8") != render_runner_guide(blueprint_value):
            raise ValueError("Runner guide is not the canonical rendering of the Anchor Blueprint")
        binding = birth.get("blueprint")
        expected_binding = {"schema": blueprint["schema"], "id": blueprint["id"], "sha256": blueprint["blueprint_sha256"]}
        if binding != expected_binding:
            raise ValueError("BIRTH.json is not bound to the carried Anchor Blueprint")
        bio_binding = bio.get("anchor_blueprint", {})
        if {k: bio_binding.get(k) for k in ("schema", "id", "sha256")} != expected_binding:
            raise ValueError("Bio-Software Anchor Blueprint binding mismatch")
        declared_interfaces = {
            interface["name"]
            for contract in blueprint["systems"]
            for interface in contract["interfaces"]
        }
        body_interfaces = {
            interface.get("name")
            for system in systems.get("systems", [])
            for interface in system.get("interfaces", [])
        }
        if not declared_interfaces <= body_interfaces:
            raise ValueError("Anchor Blueprint interface missing from Body systems")
    elif birth.get("blueprint") is not None:
        raise ValueError("BIRTH.json declares a Blueprint binding but Cartridge does not carry it")
    from .attachments import validate as validate_attachments
    validate_attachments(root)
    verify_lock(root)
    manifest = verify_manifest(root)
    return {
        "schema": "mantle.verify/1",
        "result": "PASS",
        "cartridge_id": cartridge.get("cartridge_id"),
        "bio_software": bio.get("id"),
        "persona": birth["primer"]["persona_name"],
        "systems": len(ids),
        "interfaces": len(interfaces),
        "bound_interfaces": sorted(portable_bound),
        "host_bound_interfaces": sorted(name for name, spec in interfaces.items() if spec.get("binding") == "HOST_BOUND"),
        "unavailable_interfaces": sorted(name for name, spec in interfaces.items() if spec.get("binding") == "UNAVAILABLE"),
        "tracked_files": len(manifest["files"]),
        "primer_locked": True,
        "birth_contract": True,
        "distribution_role": birth["distribution"]["role"],
        "mutable": birth["distribution"]["mutable"],
        "anchor_blueprint": bool(blueprint_decl),
    }


def pack(root: str | Path, output: str | Path):
    root, output = Path(root).resolve(), Path(output).resolve()
    validate_portable_tree(root)
    verify(root)
    if output.exists() or output.is_relative_to(root):
        raise ValueError("Output already exists or is inside Body")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(root.rglob("*")):
            if not p.is_file() or p.is_symlink() or any(part in {".git","__pycache__"} for part in p.relative_to(root).parts) or p.suffix==".pyc":
                continue
            rel = p.relative_to(root).as_posix()
            info = zipfile.ZipInfo(rel)
            info.date_time = (2026, 1, 1, 0, 0, 0)
            mode = 0o755 if os.access(p, os.X_OK) else 0o644
            info.external_attr = (stat.S_IFREG | mode) << 16
            z.writestr(info, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
    return {"output": str(output), "sha256": sha(output.read_bytes()), "bytes": output.stat().st_size}


def unpack(archive: str | Path, output: str | Path):
    archive, output = Path(archive), Path(output)
    if output.exists():
        raise ValueError("Restore output already exists")
    output.mkdir(parents=True)
    try:
        with zipfile.ZipFile(archive) as z:
            infos = z.infolist()
            if len(infos) > MAX_ARCHIVE_FILES:
                raise ValueError("Cartridge archive contains too many members")
            if sum(i.file_size for i in infos) > MAX_ARCHIVE_UNCOMPRESSED:
                raise ValueError("Cartridge archive exceeds uncompressed size limit")
            seen = set()
            for info in infos:
                rel = Path(info.filename)
                normalized = rel.as_posix().rstrip("/").casefold()
                if normalized in seen:
                    raise ValueError("Duplicate Cartridge archive member: " + normalized)
                seen.add(normalized)
                if rel.is_absolute() or ".." in rel.parts or "\\" in info.filename or ":" in info.filename or any(part.endswith(("."," ")) for part in rel.parts):
                    raise ValueError("Unsafe archive path")
                mode = (info.external_attr >> 16) & 0o170000
                if mode == stat.S_IFLNK:
                    raise ValueError("Symlinks are not allowed in a Cartridge")
                dest = output / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not info.is_dir():
                    dest.write_bytes(z.read(info))
                    perms = (info.external_attr >> 16) & 0o777
                    if perms:
                        dest.chmod(perms)
        return verify(output)
    except Exception:
        import shutil
        shutil.rmtree(output, ignore_errors=True)
        raise
