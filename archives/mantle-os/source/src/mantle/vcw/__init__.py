"""mantle.vcw -- the durable PNG-layer memory substrate (Mantle OS).

Doctrine preserved: durable PNG-layer memory, named bands, immutable hashed entries, the
veil, staged save -> verify -> atomic replace, append before overwrite, capacity triggers
metabolism (overflow 0.75 / emergency 0.90) -- never rebirth.
"""
from .png import (VCW_FORMAT, LAYER_COUNT, SIDE, CHANNELS, LAYER_BYTES,
                  encode_png_rgba, decode_png_rgba, build_layer_rgba, parse_layer_rgba)
from .entry import entry_hash, content_hash, make_entry, visible, VOLATILE_FIELDS
from .bands import (make_band_boot, make_cube_boot, standard_genome, code_hash,
                    Driver, register, get_driver, registered_encodings,
                    OVERFLOW_THRESHOLD, EMERGENCY_THRESHOLD, APP_BAND_RANGE, TAIL_RANGE)
from .drivers import (LogJsonDriver, KeyValueDriver, CalendarSpatialDriver, ExecDriver,
                      GrimoireV09Driver, GrimoireV010Driver,
                      CapabilityError, IntegrityError, TrustError, SandboxError,
                      ProvenanceError, validate_skill_code, validate_calcify_payload,
                      provenance_is_trusted, trial, register_runner, get_runner)
from .cube import Cube, CapacityError, SealError
from .atlas import ATLAS_FORMAT, VCW_ATLAS, build_atlas, verify_atlas
from . import metabolism

__all__ = [
    "VCW_FORMAT", "LAYER_COUNT", "SIDE", "CHANNELS", "LAYER_BYTES",
    "encode_png_rgba", "decode_png_rgba", "build_layer_rgba", "parse_layer_rgba",
    "entry_hash", "content_hash", "make_entry", "visible", "VOLATILE_FIELDS",
    "make_band_boot", "make_cube_boot", "standard_genome", "code_hash",
    "Driver", "register", "get_driver", "registered_encodings",
    "OVERFLOW_THRESHOLD", "EMERGENCY_THRESHOLD", "APP_BAND_RANGE", "TAIL_RANGE",
    "LogJsonDriver", "KeyValueDriver", "CalendarSpatialDriver", "ExecDriver",
    "GrimoireV09Driver", "GrimoireV010Driver",
    "CapabilityError", "IntegrityError", "TrustError", "SandboxError", "ProvenanceError",
    "validate_skill_code", "validate_calcify_payload", "provenance_is_trusted", "trial",
    "register_runner", "get_runner", "Cube", "CapacityError", "SealError", "metabolism",
    "ATLAS_FORMAT", "VCW_ATLAS", "build_atlas", "verify_atlas",
]
