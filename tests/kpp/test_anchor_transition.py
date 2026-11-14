"""Data-only Anchor logical transition trace acceptance and negative tests."""
import copy
import unittest

from mantleos import anchor_transition as t


def specimen():
    before = {"text": "", "revision": 0, "dirty": False}
    after = {"text": "Hello", "revision": 1, "dirty": True}
    step = {
        "id": "S1",
        "stimulus": {"action": "insert", "payload": {"text": "Hello"}},
        "before": copy.deepcopy(before),
        "gate": {"family": "G-COMMIT", "decision": "admit", "clauses": ["G-CMD-02"]},
        "transition": "changed",
        "after": after,
        "effects": [],
        "output": {"kind": "snapshot"},
        "evidence": {"kind": "none", "ref": None}
    }
    return {
        "schema": t.SCHEMA, "authority": "NONE", "baker_acceptance": "NOT_GRANTED",
        "contract_ref": "Notepad Fidelity 9 logical contract (illustrative)",
        "initial_state": before, "steps": [step], "final_state": after
    }


class TransitionTraceTests(unittest.TestCase):
    def setUp(self):
        self.trace = specimen()

    def test_pass_is_not_execution(self):
        result = t.validate(self.trace)
        self.assertEqual(result["semantic_execution"], "NOT_PERFORMED")
        self.assertEqual(result["baker_acceptance"], "NOT_GRANTED")

    def test_duplicate_json_keys(self):
        with self.assertRaises(t.TraceError):
            t.loads(b'{"a":1,"a":2}')

    def test_nonfinite_json(self):
        with self.assertRaises(t.TraceError):
            t.loads(b'{"a":NaN}')

    def test_authority_tamper(self):
        self.trace["authority"] = "APPROVED"
        with self.assertRaises(t.TraceError):
            t.validate(self.trace)

    def test_input_chain_tamper(self):
        self.trace["steps"][0]["before"]["text"] = "other"
        with self.assertRaises(t.TraceError):
            t.validate(self.trace)

    def test_mislabelled_transition(self):
        self.trace["steps"][0]["transition"] = "unchanged"
        with self.assertRaises(t.TraceError):
            t.validate(self.trace)

    def test_rejected_cannot_mutate_state(self):
        self.trace["steps"][0]["gate"]["decision"] = "reject"
        with self.assertRaises(t.TraceError):
            t.validate(self.trace)

    def test_observed_effect_requires_evidence(self):
        self.trace["steps"][0]["effects"] = [
            {"id": "file.write", "status": "observed-success", "evidence_ref": None}
        ]
        with self.assertRaises(t.TraceError):
            t.validate(self.trace)

    def test_undetermined_stops_at_known_state(self):
        self.trace["steps"][0]["gate"]["decision"] = "undetermined"
        self.trace["steps"][0]["transition"] = "undetermined"
        self.trace["steps"][0]["after"] = None
        self.trace["final_state"] = self.trace["initial_state"]
        self.assertEqual(t.validate(self.trace)["steps"], 1)

    def test_bool_is_not_int(self):
        self.trace["steps"][0]["before"] = copy.deepcopy(self.trace["initial_state"])
        self.trace["steps"][0]["before"]["revision"] = False
        with self.assertRaises(t.TraceError):
            t.validate(self.trace)


if __name__ == "__main__":
    unittest.main()
