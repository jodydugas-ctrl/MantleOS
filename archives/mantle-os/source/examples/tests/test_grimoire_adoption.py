from pathlib import Path

import pytest

from mantle import spore
from mantle.core.body import Body
from mantle.vcw.grimoire_editions import adopt_v010, new_grimoire_params


def test_new_spore_defaults_to_v010_and_legacy_can_be_explicit(tmp_path: Path):
    current = tmp_path / "current.png"
    legacy = tmp_path / "legacy.png"
    spore.create_spore("Current", "new tissue", path=str(current))
    spore.create_spore("Legacy", "old carrier", path=str(legacy), profile="grimoire-v0.9")
    assert spore.read_spore(str(current))["header"]["grimoire_profile"] == "grimoire-v0.10"
    assert spore.read_spore(str(legacy))["header"]["grimoire_profile"] == "grimoire-v0.9"


def test_adoption_receipt_is_operator_authorized_and_body_owned():
    body = Body()
    receipt = adopt_v010(
        body=body,
        operator_authorized=True,
        commit="adoption-test",
        repository_root=Path(__file__).resolve().parents[2],
    )
    assert receipt["edition"] == "grimoire-v0.10"
    assert receipt["default_scope"] == "new-tissue-only"
    assert body.self_record()["edition_adoptions"] == [receipt]
    assert body.__class__.from_dict(body.to_dict()).self_record()["edition_adoptions"] == [receipt]


def test_adoption_requires_operator_authority():
    with pytest.raises(PermissionError):
        adopt_v010(body=Body(), operator_authorized=False, commit="refused")


def test_new_grimoire_params_are_explicit():
    assert new_grimoire_params() == {"profile": "grimoire-v0.10"}
