#!/usr/bin/env python3
"""
mantle.vcw.atlas -- canonical VCW anatomical measurement facts.

The atlas consolidates existing cube, band, spore, and measurement rules. It is
not a new storage format and it does not drive rendering; live code remains the
source of behavioural truth. This module exposes those facts in one
machine-readable surface so documentation and audits do not need to copy them.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .png import VCW_FORMAT, LAYER_COUNT, SIDE, CHANNELS, LAYER_BYTES
from .bands import (APP_BAND_ATLAS, APP_BAND_RANGE, TAIL_RANGE,
                    app_band_reserved_spans, standard_genome)

ATLAS_FORMAT = "vcw-anatomical-atlas-v1"

MEASUREMENT_RULES = {
    "deterministic_rendering": (
        "measurement views are generated from canonical state with no LLM or "
        "random input"
    ),
    "measurement_scaling": (
        "inspectors must use nearest-neighbor scaling; interpolation changes "
        "measured pixels"
    ),
    "private_tissue": (
        "private or veiled tissue may be marked as private but must not expose "
        "its content across the public boundary"
    ),
    "content_vs_activity_colour": (
        "content colour stores payload or spatial state; activity colour reports "
        "status/pressure and is not canonical payload"
    ),
    "lane_semantics_are_profiled": (
        "RGBA are substrate lanes; the cube boot and layer driver/profile declare "
        "what the lanes mean for that layer"
    ),
}


def _region(x: int, y: int, width: int, height: int) -> Dict[str, int]:
    return {"x": x, "y": y, "width": width, "height": height}


def _spore_regions() -> Dict[str, Any]:
    from .. import spore

    vcw = _region(spore.VCW_X, spore.VCW_Y, spore.VCW_W, spore.VCW_H)
    display = _region(spore.DISP_X, spore.DISP_Y, spore.DISP_W, spore.DISP_H)
    boot_strip = _region(spore.DISP_X, spore.DISP_Y,
                         spore.DISP_W, spore.BOOT_STRIP_H)
    return {
        "format": spore.SPORE_FORMAT,
        "canvas": _region(0, 0, spore.CANVAS_W, spore.CANVAS_H),
        "vcw_region": vcw,
        "display_region": display,
        "boot_strip_region": boot_strip,
        "payload_encoding": "grimoire-v0.10-quoted-bytes (v0.9 legacy accepted)",
        "statement_integrity": "profile-specific G=0x7f PARITY over RGBA",
        "container_integrity": "SHA-256 over raw payload RGBA lanes and frame boundaries",
        "alpha_lane": "force (HEAD=QUOTE; non-HEAD semantic morphemes inherit with A=0)",
        "address_formula": "pixel_index -> (VCW_X + i % VCW_W, VCW_Y + i // VCW_W)",
        "vcw_capacity_bytes": spore.VCW_CAPACITY_BYTES,
    }


def _standard_band_ranges() -> List[Dict[str, Any]]:
    rows = []
    for boot in standard_genome():
        head = int(boot["head"])
        span = int(boot.get("span", 1))
        rows.append({
            "band": boot["band"],
            "head": head,
            "end_exclusive": head + span,
            "span": span,
            "encoding": boot["encoding"],
            "private": bool(boot.get("private")),
            "purpose": boot.get("purpose", boot["band"]),
        })
    return rows


def _reserved_app_ranges() -> List[Dict[str, Any]]:
    return [
        {"band": name, "head": head, "end_exclusive": end, "span": end - head}
        for head, end, name in app_band_reserved_spans()
    ]


def _regions_overlap(a: Dict[str, int], b: Dict[str, int]) -> bool:
    return (
        a["x"] < b["x"] + b["width"]
        and b["x"] < a["x"] + a["width"]
        and a["y"] < b["y"] + b["height"]
        and b["y"] < a["y"] + a["height"]
    )


def build_atlas() -> Dict[str, Any]:
    spore_regions = _spore_regions()
    return {
        "atlas_format": ATLAS_FORMAT,
        "cube": {
            "format": VCW_FORMAT,
            "layer_count": LAYER_COUNT,
            "layer_count_role": "canonical visualization soft cap; layers materialize on demand",
            "layer_width": SIDE,
            "layer_height": SIDE,
            "channels": CHANNELS,
            "lanes": ["R", "G", "B", "A"],
            "lane_semantics": "boot/profile-defined",
            "layer_bytes": LAYER_BYTES,
            "byte_address_formula": "offset = (y * SIDE + x) * CHANNELS",
            "png_profile": "non-interlaced 8-bit RGBA",
        },
        "bands": {
            "standard_genome": _standard_band_ranges(),
            "app_band_range": {
                "head": APP_BAND_RANGE[0],
                "end_inclusive": APP_BAND_RANGE[1],
            },
            "tail_range": {
                "head": TAIL_RANGE[0],
                "end_inclusive": TAIL_RANGE[1],
            },
            "reserved_app_bands": _reserved_app_ranges(),
        },
        "spore": spore_regions,
        "measurement_rules": dict(MEASUREMENT_RULES),
    }


def verify_atlas() -> List[str]:
    atlas = build_atlas()
    problems: List[str] = []
    cube = atlas["cube"]
    if cube["format"] != VCW_FORMAT:
        problems.append("cube format drift")
    if (cube["layer_count"], cube["layer_width"], cube["layer_height"],
            cube["channels"], cube["layer_bytes"]) != (
                LAYER_COUNT, SIDE, SIDE, CHANNELS, LAYER_BYTES):
        problems.append("cube geometry drift")
    app_ranges = {
        row["band"]: (row["head"], row["span"])
        for row in atlas["bands"]["reserved_app_bands"]
    }
    if app_ranges != APP_BAND_ATLAS:
        problems.append("reserved app-band atlas drift")
    spore = atlas["spore"]
    if ("grimoire-v0.10-quoted-bytes" not in spore["payload_encoding"]
            or spore["alpha_lane"] !=
            "force (HEAD=QUOTE; non-HEAD semantic morphemes inherit with A=0)"
            or "G=0x7f PARITY" not in spore["statement_integrity"]
            or "SHA-256" not in spore["container_integrity"]):
        problems.append("spore Grimoire v0.9 carrier encoding drift")
    if _regions_overlap(spore["vcw_region"], spore["display_region"]):
        problems.append("spore VCW and display regions overlap")
    required_rules = {
        "deterministic_rendering",
        "measurement_scaling",
        "private_tissue",
        "content_vs_activity_colour",
        "lane_semantics_are_profiled",
    }
    if set(atlas["measurement_rules"]) != required_rules:
        problems.append("measurement rule set drift")
    return problems


VCW_ATLAS = build_atlas()


__all__ = [
    "ATLAS_FORMAT",
    "MEASUREMENT_RULES",
    "VCW_ATLAS",
    "build_atlas",
    "verify_atlas",
]
