"""Tool schemas shown to the model by Hermes."""

MANTLE_STATUS = {
    "name": "mantle_status",
    "description": (
        "Inspect the bundled Mantle OS reference implementation and report its "
        "version and available command surface. This operation is read-only."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
}

MANTLE_RECORD_DISCOVERY = {
    "name": "mantle_record_discovery",
    "description": (
        "Record one bounded, inferred idea in the resident Mantle Body. The entry "
        "is explicitly unverified, is written only to the discoveries band through "
        "Limbs, and cannot modify facts, Primer, Genome, or host files."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "idea": {
                "type": "string",
                "minLength": 1,
                "maxLength": 2000,
                "description": "The inferred idea to preserve; never include secrets.",
            }
        },
        "required": ["idea"],
        "additionalProperties": False,
    },
}
