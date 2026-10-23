from __future__ import annotations

from pathlib import Path

from mantleos.mapping import map_body


def _map(root: Path) -> dict:
    return map_body(
        root,
        source_uri="https://github.com/example/body",
        source_fingerprint="sha256:" + "0" * 64,
    )


def test_python_body_genome_accounts_for_files_symbols_calls_and_loops(tmp_path: Path):
    (tmp_path / "main.py").write_text(
        """def heartbeat_loop():
    while True:
        save_state()

def helper(items):
    for item in items:
        print(item)
""",
        encoding="utf-8",
    )
    mapped = _map(tmp_path)

    assert mapped["genome_schema"] == "mantle.body-genome.v2"
    assert mapped["coverage"]["tier"] == "mapping-complete"
    assert mapped["coverage"]["states"] == {"complete": 1}
    assert {item["symbol"] for item in mapped["graphs"]["symbols"]} == {
        "heartbeat_loop",
        "helper",
    }
    assert mapped["coverage"]["loops"]["total"] == 2
    assert {item["disposition"] for item in mapped["loops"]} == {
        "blocked-insufficient-evidence",
        "local-utility-no-direct-nerve",
    }
    assert mapped["coverage"]["loops"]["undispositioned_major_arteries"] == 1


def test_structural_fallback_is_useful_but_never_claimed_complete(tmp_path: Path):
    (tmp_path / "main.ts").write_text(
        """async function runAgent() {
  while (running) { await receiveMessage(); }
}
""",
        encoding="utf-8",
    )
    mapped = _map(tmp_path)

    assert mapped["coverage"]["tier"] == "mapping-partial"
    assert mapped["coverage"]["states"] == {"partial": 1}
    assert mapped["loops"][0]["disposition"] == "blocked-insufficient-evidence"
    assert mapped["loops"][0]["artery_classes"]
    assert any("partial parser coverage" in item for item in mapped["unknowns"])
    assert any("major arteries" in item for item in mapped["unknowns"])


def test_qt_and_ownership_evidence_are_kept_separate(tmp_path: Path):
    (tmp_path / "CMakeLists.txt").write_text("project(Body LANGUAGES CXX)\n", encoding="utf-8")
    (tmp_path / "main.cpp").write_text(
        """int main(int argc, char **argv) {
  while (running) { processEvents(); }
  connect(sender, &Sender::ready, receiver, &Receiver::receiveMessage);
}
""",
        encoding="utf-8",
    )
    vendor = tmp_path / "third_party"
    vendor.mkdir()
    (vendor / "dependency.cpp").write_text("void dep() { while (true) {} }\n", encoding="utf-8")

    mapped = _map(tmp_path)
    coverage = mapped["coverage"]
    assert coverage["ownership"] == {"first-party": 2, "vendored": 1}
    assert coverage["tier"] == "mapping-partial"
    assert mapped["build_systems"] == ["cmake"]
    assert mapped["behavior_surfaces"] == ["lifecycle", "native-graphical-interface"]
    assert len(mapped["graphs"]["events"]) == 1
    assert all(item["path"] != "third_party/dependency.cpp" for item in mapped["loops"])


def test_unknown_language_stops_at_honest_inventory_tier(tmp_path: Path):
    (tmp_path / "program.xyz").write_text("forever do work\n", encoding="utf-8")
    mapped = _map(tmp_path)
    assert mapped["coverage"]["tier"] == "inventory-only"
    assert "No source language was identified" in mapped["unknowns"]
    assert "No known application entrypoint was identified" in mapped["unknowns"]


def test_oversized_source_is_hashed_but_not_loaded_into_parser(tmp_path: Path):
    (tmp_path / "large.py").write_bytes(b"#" * (2 * 1024 * 1024 + 1))
    mapped = _map(tmp_path)
    row = mapped["file_coverage"][0]
    assert row["state"] == "blocked"
    assert row["sha256"]
    assert row["limitations"][0].startswith("source-too-large:")
    assert mapped["coverage"]["tier"] == "mapping-blocked"


def test_text_hashes_and_maps_are_independent_of_checkout_line_endings(tmp_path: Path):
    lf = tmp_path / "lf"
    crlf = tmp_path / "crlf"
    lf.mkdir()
    crlf.mkdir()
    source = "def main():\n    while True:\n        break\n"
    (lf / "main.py").write_bytes(source.encode())
    (crlf / "main.py").write_bytes(source.replace("\n", "\r\n").encode())
    assert _map(lf) == _map(crlf)
