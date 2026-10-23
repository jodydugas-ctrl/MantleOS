from __future__ import annotations

from pathlib import Path

import pytest

from mantle import spore
from mantle.vcw.grimoire import (
    EVIDENCE,
    FORCE,
    GrimoireDecodeError,
    decode_quoted_bytes,
    encode_quoted_bytes,
    parity_pixel,
)


def _payload_frame(path: Path) -> tuple[object, int, bytes]:
    img = spore._read_png(str(path))
    _, start = spore._read_frame(img.load(), 0, "test-header")
    raw, _ = spore._read_frame(img.load(), start, "test-payload")
    return img, start, raw


def _rewrite_frame(path: Path, img, start: int, raw: bytes) -> None:
    data = bytearray(img._rgba)
    offset = start * 4
    data[offset:offset + len(raw)] = raw
    spore._write_png(str(path), img.size[0], img.size[1], data, dict(img.text))


def test_v09_tables_and_quoted_byte_alpha_policy():
    assert EVIDENCE == {
        0x00: "INHERIT",
        0x01: "DIRECT",
        0x02: "MEASURED",
        0x03: "CITED",
        0x04: "INFERRED",
        0x05: "REMEMBERED",
        0x06: "REPORTED",
        0x07: "ASSUMED",
        0x08: "STIPULATED",
        0x09: "UNKNOWN",
    }
    assert FORCE == {
        0x00: "INHERIT",
        0x01: "LAW",
        0x02: "MUST",
        0x03: "DUTY",
        0x04: "NEVER",
        0x05: "NEED",
        0x06: "GATE",
        0x07: "BOUND",
        0x08: "RULE",
        0x09: "RIGHT",
        0x0A: "POWER",
        0x0B: "CAN",
        0x0C: "LET",
        0x0D: "MAY",
        0x0E: "WAY",
        0x0F: "QUOTE",
    }

    original = bytes(range(256))
    raw = encode_quoted_bytes(original)
    records = [tuple(raw[i:i + 4]) for i in range(0, len(raw), 4)]
    assert records[0][1:] == (0x01, 0x01, 0x0F)
    assert all(record[1:] == (0x40, 0x00, 0x00)
               for record in records[1:-1])
    assert records[-1][1] == 0x7F
    assert decode_quoted_bytes(raw) == original


def test_parity_substitutes_only_zero_r():
    records = [
        (0x01, 0x01, 0x01, 0x0F),
        (0x01, 0x40, 0x01, 0x0F),
    ]
    assert parity_pixel(records) == (0xFE, 0x7F, 0x00, 0x00)


def test_single_lane_corruption_rejected_by_statement_parity(tmp_path: Path):
    path = tmp_path / "parity.png"
    spore.create_spore("Parity", "reject one changed lane", path=str(path),
                       profile="grimoire-v0.9")
    img, start, raw = _payload_frame(path)
    damaged = bytearray(raw)
    damaged[0] ^= 0x01
    _rewrite_frame(path, img, start, bytes(damaged))

    with pytest.raises(ValueError, match="PARITY mismatch"):
        spore.read_spore(str(path))


def test_parity_preserving_rewrite_rejected_by_full_lane_fingerprint(
        tmp_path: Path):
    path = tmp_path / "fingerprint.png"
    spore.create_spore("Fingerprint", "reject rewritten raw lanes", path=str(path),
                       profile="grimoire-v0.9")
    img, start, raw = _payload_frame(path)
    records = [list(raw[i:i + 4]) for i in range(0, len(raw), 4)]
    records[0][0] = 1 if records[0][0] != 1 else 2
    records[-1] = list(parity_pixel(tuple(record) for record in records[:-1]))
    rewritten = b"".join(bytes(record) for record in records)
    assert decode_quoted_bytes(rewritten) != decode_quoted_bytes(raw)
    _rewrite_frame(path, img, start, rewritten)

    with pytest.raises(ValueError, match="full-lane fingerprint mismatch"):
        spore.read_spore(str(path))


def test_strict_parser_refuses_non_rgba_png(tmp_path: Path):
    if spore.Image is None:
        pytest.skip("Pillow unavailable")
    path = tmp_path / "rgb.png"
    spore.Image.new("RGB", (spore.CANVAS_W, spore.CANVAS_H)).save(path, "PNG")
    with pytest.raises(ValueError, match="non-interlaced 8-bit RGBA"):
        spore.read_spore(str(path))


def test_legacy_alpha_ecc_api_is_removed():
    assert not hasattr(spore, "compute_T")
    assert not hasattr(spore, "decode_T")
    source = Path(spore.__file__).read_text(encoding="utf-8").lower()
    assert "hamming" not in source
    assert "secded" not in source
