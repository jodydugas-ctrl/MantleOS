"""Hermetic segment-reconstruction tests (GHNEST-20 machinery)."""
import pytest

from mantle.nest.segments import (
    SegmentError,
    fingerprint_equal,
    reconstruct,
    slice_segments,
)


def test_segment_roundtrip_is_equivalent():
    data = b"A complete content-addressed VCW checkpoint " * 4  # 144 bytes, divisible by 4/6
    headers = slice_segments(data, 4)
    size = len(data) // 4
    by = {h.index: data[h.index * size:(h.index + 1) * size] for h in headers}
    out = reconstruct(headers, lambda h: by[h.index])
    assert out == data
    from mantle.nest.manifest import sha256_bytes

    assert fingerprint_equal(out, sha256_bytes(data))


def test_tampered_segment_detected():
    data = b"X" * 100
    headers = slice_segments(data, 3)
    by = {h.index: data[h.index * 33:(h.index + 1) * 33] for h in headers}
    by[1] = by[1][:-1] + b"Y"
    with pytest.raises(SegmentError):
        reconstruct(headers, lambda h: by[h.index])


def test_invalid_segments_rejected():
    with pytest.raises(SegmentError):
        reconstruct([], lambda h: b"")
