import pytest

from mantle.mind.port import MindPort
from mantle.research import ResearchPort, ResearchPortError


def test_research_port_is_proposal_only():
    port = ResearchPort(protocols={"p": {"profile": "test"}}, results=[{"status": "PASS"}])
    assert port.inspect_protocol("p") == {"profile": "test"}
    assert port.inspect_results() == [{"status": "PASS"}]
    proposal = port.propose_candidate({"hypothesis": "smaller"})
    assert proposal["author"] == "MIND" and proposal["status"] == "PROPOSED"
    request = port.request_trial(proposal["proposal_id"])
    assert request["authorized"] is False
    assert port.request_future_pulse(proposal["proposal_id"], 2)["authorized"] is False
    forbidden = {"execute", "adopt", "calcify", "write", "run", "network", "organism"}
    assert not forbidden.intersection(dir(port))
    assert not hasattr(port, "organism")


def test_mind_port_cannot_write_research_ledger():
    class Dummy:
        def immune_event(self, kind, detail):
            self.event = (kind, detail)

    mind_port = MindPort(Dummy())
    with pytest.raises(PermissionError):
        mind_port.write("research_runs", {"status": "PROPOSED"})


def test_research_port_refuses_authority_fields():
    port = ResearchPort()
    with pytest.raises(ResearchPortError):
        port.propose_candidate({"adopt": True})
