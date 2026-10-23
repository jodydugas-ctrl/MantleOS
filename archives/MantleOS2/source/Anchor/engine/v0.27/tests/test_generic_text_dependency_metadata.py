from pathlib import Path

from scan.adapters.generic_text import GenericTextAdapter
from scan.inventory import record_from_bytes


def test_package_lock_urls_remain_repository_evidence(tmp_path: Path):
    text = '{"resolved":"https://registry.example.invalid/pkg.tgz","plugin":"metadata"}\n'
    rec = record_from_bytes("package-lock.json", text.encode("utf-8"))
    result = GenericTextAdapter().extract(tmp_path, rec, text)

    assert result.nodes
    assert all(node.kind == "repository_reference" for node in result.nodes)
    assert all((node.attributes or {}).get("reference_context") == "dependency_metadata" for node in result.nodes)
    assert not any(node.kind in {"nest_boundary", "extension_receptor_candidate"} for node in result.nodes)


def test_runtime_source_url_can_still_be_a_nest_candidate(tmp_path: Path):
    text = 'const endpoint = "https://api.example.invalid/v1"\n'
    rec = record_from_bytes("src/client.ts", text.encode("utf-8"))
    result = GenericTextAdapter().extract(tmp_path, rec, text)

    urls = [n for n in result.nodes if (n.attributes or {}).get("generic_kind") == "url"]
    assert len(urls) == 1
    assert urls[0].kind == "nest_boundary"
    assert urls[0].coverage == "PARTIAL"
