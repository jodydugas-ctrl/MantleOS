"""Canonical Mantle 2 terminal for the NotepadNext candidate."""
from __future__ import annotations

import getpass
import sys

from mantle.contracts import EvidenceRef, HostAdapter, ResidentRuntime
from mantle.core.organism import Organism
from mantle.resident.commands import BodyCommandDispatcher, BodyCommandResult


HOST_COMMIT = "0e9694d98aa8a9962bbe2bfa9dd502931be33670"


class NotepadNextAdapter(HostAdapter):
    def host_evidence(self):
        return (
            EvidenceRef("git-commit", "notepadnext-source", "dail8859/NotepadNext",
                        location=HOST_COMMIT),
            EvidenceRef("assimilation-map", "notepadnext-qt-graph",
                        "Mantle read-only native/Qt scan"),
        )

    def working_surfaces(self):
        return (
            {"id": "editor", "type": "document", "alias": "active document"},
            {"id": "terminal", "type": "conversation"},
        )


def build_runtime(org):
    dispatcher = BodyCommandDispatcher(org)

    def surfaces(_argument, _secret):
        rows = list(NotepadNextAdapter().working_surfaces())
        return BodyCommandResult(
            "/surfaces", True, "executed", "Observed NotepadNext working surfaces: editor, terminal.",
            details={"surfaces": rows, "mutation": False},
        )

    dispatcher.register("/surfaces", "show observed NotepadNext surfaces", surfaces)
    return ResidentRuntime(dispatcher, NotepadNextAdapter())


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print("usage: terminal.py <candidate-resident>")
        return 2
    org = Organism.load(argv[0], verify_seals=True)
    runtime = build_runtime(org)
    print("NotepadNext.AppAI Mantle 2 candidate (%s)" % runtime.PROTOCOL_VERSION)
    while True:
        try:
            line = input("you> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if line.strip() == "/key":
            secret = getpass.getpass("OpenRouter key (hidden; blank cancels): ")
            result = runtime.dispatcher.dispatch("/key", secret_input=secret or None)
            print(result.message)
            continue
        result = runtime.turn(line)
        print(result.visible_output)
        if line.strip() in ("/quit", "/exit"):
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
