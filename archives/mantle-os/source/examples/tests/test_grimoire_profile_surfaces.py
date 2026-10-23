from mantle.compiler import GenomeError, validate_genome
from mantle.vcw import Cube, make_band_boot, registered_encodings, standard_genome
from mantle.vcw.grimoire_editions.v010 import SELFTEST_VECTORS


def test_both_grimoire_drivers_are_registered():
    assert "grimoire-v0.9" in registered_encodings()
    assert "grimoire-v0.10" in registered_encodings()


def test_v010_driver_requires_and_persists_profile():
    boot = make_band_boot(
        "v010", 600, "grimoire-v0.10", span=1,
        params={"profile": "grimoire-v0.10"},
    )
    cube = Cube.genesis(standard_genome() + [boot])
    cube.append("v010", {"profile": "grimoire-v0.10", "raw": SELFTEST_VECTORS[0]})
    assert cube.retrieve("v010", 0)["profile"] == "grimoire-v0.10"


def test_v010_compiler_requires_explicit_profile():
    try:
        validate_genome([{"band": "v010", "head": 600, "encoding": "grimoire-v0.10"}])
    except GenomeError as exc:
        assert "explicit profile" in str(exc)
    else:
        raise AssertionError("v0.10 compiler accepted an implicit profile")
