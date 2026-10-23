#!/usr/bin/env python3
"""
mantle.face  --  the CHROMATOPHORE: the organism draws its own portrait (Mantle OS)

An octopus renders its inner state on its skin -- color and pattern as a living
display. The VCW already stores memory as real images; the face closes the loop: the
ORGANISM ITSELF paints a real PNG of its own condition, deterministically, with no
LLM and no graphics library (the same hand-rolled PNG codec the cube uses).

The portrait shows, as colored tissue:
  * one row per band: allocation pressure as a bar (green -> amber at 0.75 ->
    red at 0.90), entry count as brightness ticks
  * the organ strip: one block per canonical organ (ORGAN_ORDER), Brain dim while
    dormant, lit when fused
  * the lineage strip: one sealed-ancestor block per generation
  * the immune margin: recent immune events as red ticks

Pictures, answered organically: the best diagram of an organism's state is the one it
draws itself.   `python -m mantle face <organism-dir> [out.png]`
"""
from __future__ import annotations

from typing import Any, Tuple

from .vcw.png import encode_png_rgba

W, H = 800, 480
CH = 4

# tissue palette (RGBA)
BG      = (15, 23, 42, 255)       # deep sea
PANEL   = (30, 41, 59, 255)
TEXTROW = (148, 163, 184, 255)
GREEN   = (34, 197, 94, 255)
AMBER   = (245, 158, 11, 255)
RED     = (239, 68, 68, 255)
BLUE    = (96, 165, 250, 255)
VIOLET  = (167, 139, 250, 255)
DIM     = (71, 85, 105, 255)
LIT     = (250, 204, 21, 255)


class _Canvas:
    def __init__(self, w: int = W, h: int = H) -> None:
        self.w, self.h = w, h
        self.buf = bytearray(w * h * CH)
        self.rect(0, 0, w, h, BG)

    def px(self, x: int, y: int, c: Tuple[int, int, int, int]) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            o = (y * self.w + x) * CH
            self.buf[o:o + CH] = bytes(c)

    def rect(self, x: int, y: int, w: int, h: int, c) -> None:
        row = bytes(c) * max(0, min(w, self.w - x))
        for yy in range(y, min(y + h, self.h)):
            o = (yy * self.w + x) * CH
            self.buf[o:o + len(row)] = row

    def png(self) -> bytes:
        return encode_png_rgba(bytes(self.buf), self.w, self.h)


def render(org: Any, out_path: str) -> str:
    """Paint the organism's self-portrait to a real PNG file. Deterministic."""
    c = _Canvas()

    # ---- band rows: pressure bars -----------------------------------------
    y = 24
    bar_x, bar_w, row_h = 200, 520, 30
    for name, boot in org.prime.bands.items():
        p = org.prime.pressure(name)
        color = RED if p >= 0.90 else AMBER if p >= 0.75 else GREEN
        c.rect(24, y, 160, 18, VIOLET if boot.get("private") else PANEL)   # name plate
        c.rect(bar_x, y, bar_w, 18, PANEL)                                  # trough
        c.rect(bar_x, y, max(2, int(bar_w * min(p, 1.0))), 18, color)      # pressure
        # threshold notches at 0.75 / 0.90
        c.rect(bar_x + int(bar_w * 0.75), y - 3, 2, 24, AMBER)
        c.rect(bar_x + int(bar_w * 0.90), y - 3, 2, 24, RED)
        # brightness ticks: one per 5 visible entries (capped)
        n = len(org.prime.read(name, reveal_private=True)) if boot["encoding"] == "log-json" else 0
        for i in range(min(n // 5 + (1 if n else 0), 40)):
            c.px(26 + i * 4, y + 22, BLUE)
            c.px(27 + i * 4, y + 22, BLUE)
        y += row_h

    # ---- organ strip: one block per canonical organ, Brain lit only when fused
    from .core.organism import ORGAN_ORDER
    y += 16
    ox = 24
    step = (W - 48) // len(ORGAN_ORDER)          # fit however many organs the mesh has
    for organ_name in ORGAN_ORDER:
        lit = not (organ_name == "brain" and not org.brain.fused)
        c.rect(ox, y, step - 8, 34, LIT if (organ_name == "brain" and org.brain.fused)
               else (GREEN if lit else DIM))
        ox += step

    # ---- lineage strip: one sealed block per ancestor + the hot prime ------
    y += 50
    ox = 24
    for anc in org.ancestral:
        c.rect(ox, y, 40, 22, DIM)        # sealed, cold
        c.rect(ox, y, 40, 4, VIOLET)      # the seal
        ox += 48
    c.rect(ox, y, 40, 22, BLUE)           # the Prime, hot

    # ---- immune margin: recent events as red ticks --------------------------
    y += 38
    for i, _evt in enumerate(org.immune.log[-60:]):
        c.rect(24 + i * 12, y, 8, 10, RED)
    if not org.immune.log:
        c.rect(24, y, 8, 10, GREEN)

    png = c.png()
    with open(out_path, "wb") as f:
        f.write(png)
    return out_path
