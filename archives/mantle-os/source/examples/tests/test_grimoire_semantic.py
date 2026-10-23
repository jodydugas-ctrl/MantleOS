#!/usr/bin/env python3
"""
test_grimoire_semantic.py  --  the semantic-memory profile (one-step encoding)

Covers `mantle.vcw.grimoire_editions.semantic` and the `grimoire-v0.10-entry`
driver/cube machinery: encoding tables (evidence/force/record-kind), round-trip
fidelity, determinism, red cases (laundering refused, invented atoms refused,
content drift detected), and the cube guarantees on a semantic band (ids, veil,
immune marks, graded memory, multi-layer reads, metabolism, durability, carrier
compatibility, adoption gate). Pure standard library; pytest only.
"""
import copy
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from mantle.vcw.bands import semantic_genome, standard_genome, make_band_boot
from mantle.vcw.cube import Cube
from mantle.vcw.entry import make_entry, entry_hash
from mantle.vcw.grimoire_editions import semantic
from mantle.vcw.grimoire_editions.semantic import (
    resolve_evidence, resolve_force, resolve_record_kind, encode_entry, decode_entry,
    COMPOSITION_ROWS, RECORD_KIND_BY_OPCODE, FORCE_BY_OPCODE, UNDIFFERENTIATED_ATOM,
)
from mantle.vcw.grimoire_editions.v010 import SELFTEST_VECTORS
from mantle.vcw.grimoire_editions.adoption import adopt_semantic_memory, new_semantic_genome_params
from mantle.vcw.grimoire_editions import SEMANTIC_MEMORY_PROFILE
from mantle.compiler import validate_genome, GenomeError
from mantle.core.body import Body


def _fixed(entry):
    """Pin ts so determinism tests compare bytes, not timestamps."""
    e = dict(entry)
    e["ts"] = 123456789.0
    return e


def _think(content=None, **extra):
    return _fixed(make_entry(content if content is not None else {"reflection": "x"},
                             opcode="THINK", author="MIND",
                             verified=False, confidence="inferred", **extra))


# ---------------------------------------------------------------------------
# encoder-level guarantees
# ---------------------------------------------------------------------------
def test_selftest_vectors():
    assert all(ok for _label, ok, _note in semantic.selftest()), semantic.selftest()


def test_round_trip_fidelity():
    entry = _think({"reflection": "round trip", "nested": {"a": [1, 2, 3]}})
    record = encode_entry(entry)
    decode_entry(record)                       # raises on any drift
    assert record["content"] == entry["content"]
    assert record["opcode"] == entry["opcode"]
    assert record["author"] == entry["author"]
    assert record["hash"] == entry_hash(record)
    # content round-trips byte-for-byte through the QUOTE frame
    bytes_back = semantic.v010.decode_quoted_bytes(record["semantic"]["content_raw"],
                                                   frame_id="t")
    assert json.loads(bytes_back.decode("utf-8")) == entry["content"]


def test_determinism():
    entry = _think({"reflection": "same"})
    a, b = encode_entry(entry), encode_entry(entry)
    assert a["semantic"]["raw"] == b["semantic"]["raw"]
    assert a["semantic"]["content_raw"] == b["semantic"]["content_raw"]
    assert a["hash"] == b["hash"]


def test_evidence_default_table():
    cases = [
        ({"verified": True, "source": "sensor-1", "opcode": "SENSE"}, "MEASURED"),
        ({"verified": True, "source": "cited work", "opcode": "WRITE"}, "CITED"),
        ({"verified": True, "source": "", "opcode": "WRITE"}, "UNKNOWN"),
        ({"opcode": "THINK", "author": "MIND"}, "INFERRED"),
        ({"opcode": "DISCOVERY", "author": "BODY"}, "INFERRED"),
        ({"opcode": "CONSOLIDATE", "author": "MIND"}, "REMEMBERED"),
        ({"opcode": "RECALL", "author": "BODY"}, "REMEMBERED"),
        ({"opcode": "WRITE", "source": "conversation"}, "REPORTED"),
        ({"opcode": "WRITE", "assumption": True}, "ASSUMED"),
        ({"opcode": "WRITE", "confidence": "assumed"}, "ASSUMED"),
        ({"opcode": "WRITE", "source": "genome policy"}, "STIPULATED"),
        ({"opcode": "WRITE", "source": "operator"}, "STIPULATED"),
        ({"content": {"x": 1}}, "UNKNOWN"),               # nothing identifiable
        ({"opcode": "WRITE", "evidence": "CITED"}, "CITED"),
        ({"opcode": "WRITE", "evidence": "DIRECT"}, "UNKNOWN"),       # never invented
        ({"opcode": "SENSE", "evidence": "DIRECT", "verified": True,
          "source": "sensor-1"}, "DIRECT"),
    ]
    for entry, expected in cases:
        assert resolve_evidence(entry) == expected, (entry, expected)


def test_force_default_table():
    expected = {
        "THINK": "MAY", "PROPOSE": "MAY", "SPECIAL": "MAY", "CONSOLIDATE": "LET",
        "DISPATCH": "GATE", "INTENTION": "GATE", "DELEGATED": "GATE", "PROOF": "BOUND",
        "IMMUNE": "MUST", "WARN": "MUST", "SENSE": "WAY", "RULE": "RULE",
        "POLICY": "RULE", "DEWEIGHT": "BOUND", "WRITE": "BOUND", "DISCOVERY": "BOUND",
        "RECALL": "WAY",
    }
    for opcode, force in expected.items():
        assert resolve_force({"opcode": opcode}) == force, (opcode, force)
    assert resolve_force({"opcode": "MODEL.REQUEST"}) == "BOUND"
    assert resolve_force({"opcode": "MYSTERY"}) == "QUOTE"     # never invented
    assert resolve_force({"opcode": "MYSTERY", "force": "WAY"}) == "WAY"
    assert resolve_force({"opcode": "RULE", "force": "LAW"}) == "QUOTE"   # no stipulation
    assert resolve_force({"opcode": "RULE", "force": "LAW",
                          "stipulated": True}) == "LAW"


def test_record_kind_coverage():
    """Every mapped opcode resolves to a canonical composition; unmapped -> 一 + QUOTE."""
    for opcode in RECORD_KIND_BY_OPCODE:
        assert resolve_record_kind(opcode) is not None, opcode
    for opcode in FORCE_BY_OPCODE:
        assert resolve_record_kind(opcode) is not None, opcode
    assert resolve_record_kind("MODEL.USAGE") is not None
    assert resolve_record_kind("MYSTERY") is None
    record = encode_entry(_fixed(make_entry({"x": 1}, opcode="MYSTERY")))
    assert record["semantic"]["force"] == "QUOTE"
    assert record["semantic"]["composition"] is None
    statement = record["semantic"]["statement"]
    assert statement["groups"][0]["atoms"][0]["r"] == UNDIFFERENTIATED_ATOM


def test_laundering_refused():
    """ASSUMED may never become INFERRED; a verified fact never becomes INFERRED."""
    assumed = _fixed(make_entry({"claim": "p"}, opcode="WRITE", assumption=True))
    assert resolve_evidence(assumed) == "ASSUMED"
    record = encode_entry(assumed)
    assert record["semantic"]["evidence"] == "ASSUMED"
    measured = _fixed(make_entry({"claim": "p"}, opcode="WRITE",
                                 verified=True, source="sensor-9"))
    assert resolve_evidence(measured) == "MEASURED"


def test_composition_rows_match_edition():
    """On a repository checkout, every mirror row must equal the edition's row."""
    rows = semantic._edition_composition_rows()
    if not rows:
        return                       # installed package: source check unavailable
    for name, (spelling, _gloss) in COMPOSITION_ROWS.items():
        assert rows[name] == spelling, (name, rows.get(name), spelling)
    assert semantic.composition_source_verified()


def test_content_drift_detected():
    record = encode_entry(_think({"reflection": "original"}))
    tampered = copy.deepcopy(record)
    tampered["content"] = {"reflection": "drifted"}
    try:
        decode_entry(tampered)
        assert False, "content drift must be refused"
    except semantic.v010.GrimoireDecodeError:
        pass


def test_tampered_raw_detected():
    record = encode_entry(_think({"reflection": "original"}))
    tampered = copy.deepcopy(record)
    tampered["semantic"]["raw"] = tampered["semantic"]["raw"][:-2] + "00"
    try:
        decode_entry(tampered)
        assert False, "raw tamper must be refused"
    except semantic.v010.GrimoireDecodeError:
        pass


# ---------------------------------------------------------------------------
# cube-level guarantees on a semantic band
# ---------------------------------------------------------------------------
def test_cube_one_step_think():
    cube = Cube.genesis(semantic_genome(), generation=0)
    entry = _think({"reflection": "hello"})
    cube.append("thoughts", entry)
    records = cube.read("thoughts", reveal_private=True)
    assert len(records) == 1
    r = records[0]
    assert r["opcode"] == "THINK" and r["author"] == "MIND"
    assert r["semantic"]["evidence"] == "INFERRED" and r["semantic"]["force"] == "MAY"
    assert r["semantic"]["composition"] == "reasoning"
    assert r["semantic"]["parity_status"] == "ok"
    assert r["hash"] == entry_hash(r)


def test_cube_veil():
    cube = Cube.genesis(semantic_genome(), generation=0)
    cube.append("thoughts", _think())
    assert cube.read("thoughts") == []
    assert len(cube.read("thoughts", reveal_private=True)) == 1


def test_cube_ids_and_marks():
    cube = Cube.genesis(semantic_genome(), generation=0)
    for i in range(3):
        cube.append("thoughts", _think({"reflection": "r%d" % i}))
    ids = [e["id"] for e in cube.read("thoughts", reveal_private=True)]
    assert ids == [0, 1, 2]
    cube.tombstone("thoughts", 1)
    assert [e["id"] for e in cube.read("thoughts", reveal_private=True)] == [0, 2]
    cube.quarantine("thoughts", 2)
    assert [e["id"] for e in cube.read("thoughts", reveal_private=True)] == [0]
    # retrieve works on the non-private brain band
    cube.append("brain", make_entry({"d": 1}, opcode="DISPATCH", author="BODY",
                                    verified=True, source="sensor-1"))
    assert cube.retrieve("brain", 0)["id"] == 0
    assert cube.retrieve("thoughts", 0) is None       # private bands veil retrieve


def test_cube_multilayer_read():
    genome = []
    for boot in standard_genome():
        if boot["band"] == "thoughts":
            boot["encoding"] = "grimoire-v0.10-entry"
            boot["params"] = {"profile": "grimoire-v0.10-entry",
                              "max_entries_per_layer": 2}
            boot["span"] = 5
        genome.append(boot)
    cube = Cube.genesis(genome, generation=0)
    for i in range(6):
        cube.append("thoughts", _think({"reflection": "m%d" % i}))
    assert cube.layer_count("thoughts") == 3
    assert [e["id"] for e in cube.read("thoughts", reveal_private=True)] == [0, 1, 2, 3, 4, 5]


def test_cube_graded_memory():
    cube = Cube.genesis(semantic_genome(), generation=0)
    cube.append("thoughts", _think({"reflection": "a"}))
    cube.append("thoughts", _think({"reflection": "b"}))
    cube.deweight("thoughts", 0)
    assert [e["id"] for e in cube.read("thoughts", reveal_private=True)] == [1]
    assert [e["id"] for e in cube.read("thoughts", reveal_private=True, ghosts=True)] == [0]
    cube.deweight("thoughts", 0, weight=0.5)
    assert [e["id"] for e in cube.read("thoughts", reveal_private=True)] == [1, 0]


def test_cube_metabolism_never_collapses_distinct_evidence():
    cube = Cube.genesis(semantic_genome(), generation=0)
    # two identical reflections (dedupe) and one distinct-evidence fact
    cube.append("thoughts", _think({"reflection": "dup"}))
    cube.append("thoughts", _think({"reflection": "dup"}))
    cube.append("thoughts", _fixed(make_entry({"reflection": "dup"}, opcode="THINK",
                                              author="BODY", verified=True,
                                              source="sensor-1", confidence="measured")))
    rep = cube.dedupe("thoughts")
    assert rep["duplicates"] == 1, rep                       # only the identical twin
    live = cube.read("thoughts", reveal_private=True)
    assert [e["id"] for e in live] == [0, 2]
    assert live[1]["semantic"]["evidence"] == "MEASURED"     # distinct evidence kept
    # compact reclaims tombstones
    cube.tombstone("thoughts", 0)
    rep = cube.compact("thoughts")
    assert rep["dropped"] == 2, rep          # dedupe-tombstoned twin + manual tombstone
    assert [e["id"] for e in cube.read("thoughts", reveal_private=True)] == [2]


def test_cube_save_load_round_trip():
    cube = Cube.genesis(semantic_genome(), generation=0)
    cube.append("thoughts", _think({"reflection": "durable"}))
    cube.append("brain", make_entry({"d": 1}, opcode="DISPATCH", author="BODY",
                                    verified=True, source="sensor-1"))
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "gen0.vcw")
        cube.save(path)
        loaded = Cube.load(path)
        back = loaded.read("thoughts", reveal_private=True)
        assert back[0]["semantic"]["raw"] == \
            cube.read("thoughts", reveal_private=True)[0]["semantic"]["raw"]
        assert loaded.read("brain")[0]["semantic"]["force"] == "GATE"
        assert loaded.verify() == []


def test_carrier_compat():
    cube = Cube.genesis(semantic_genome(), generation=0)
    cube.append("brain", {"raw": SELFTEST_VECTORS[0], "frame_id": "carrier",
                          "profile": "grimoire-v0.10"})
    decoded = cube.read("brain")[0]
    assert decoded["profile"] == "grimoire-v0.10" and decoded["parity_status"] == "ok"


# ---------------------------------------------------------------------------
# governance + compiler gates
# ---------------------------------------------------------------------------
def test_adoption_gate():
    body = Body()
    root = os.path.join(os.path.dirname(__file__), "..", "..")
    try:
        adopt_semantic_memory(body=body, operator_authorized=False, commit="abc",
                              repository_root=root)
        assert False, "unauthorized adoption must be refused"
    except PermissionError:
        pass
    assert new_semantic_genome_params() == {"profile": SEMANTIC_MEMORY_PROFILE}
    receipt = adopt_semantic_memory(body=body, operator_authorized=True, commit="abc",
                                    repository_root=root)
    assert receipt["kind"] == "semantic_memory_adoption"
    assert receipt["default_scope"] == "new-tissue-only"
    assert receipt in body.self_record()["edition_adoptions"]


def test_compiler_explicit_profile_rule():
    spec = make_band_boot("sem", 600, "grimoire-v0.10-entry", params={})
    try:
        validate_genome([spec])
        assert False, "missing explicit profile must be refused"
    except GenomeError:
        pass
    spec = make_band_boot("sem", 600, "grimoire-v0.10-entry",
                          params={"profile": "grimoire-v0.10-entry"})
    boots = validate_genome([spec])
    assert boots[0]["encoding"] == "grimoire-v0.10-entry"
    assert boots[0]["params"]["profile"] == "grimoire-v0.10-entry"


def test_semantic_genome_shape():
    genome = semantic_genome()
    boots = {b["band"]: b for b in genome}
    assert boots["thoughts"]["encoding"] == "grimoire-v0.10-entry"
    assert boots["thoughts"]["private"] is True
    assert boots["brain"]["encoding"] == "grimoire-v0.10-entry"
    assert boots["facts"]["encoding"] == "log-json"
    assert boots["identity"]["encoding"] == "log-json"
    assert boots["immune"]["encoding"] == "log-json"
