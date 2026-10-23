"""Interactive resident terminal for Organize.AppAI.

The OpenRouter credential is accepted only through a hidden prompt and remains in
process memory. Mantle energy credits are a separate local accounting mechanism.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import re
import sys
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from .assist import discover_workspace
from .bridge import MantleBridge
from .containment import require_contained

DEFAULT_MODEL = "openrouter/free"
_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+@-]{0,199}$")
SYSTEM_PROMPT = """You are the bounded MIND of Organize.AppAI, resident in the
open-source organize file-management application. Answer from the deterministic host map,
configuration evidence, and Mantle context supplied with the question. Distinguish observed,
verified, inferred, proposed, refused, and executed. Never claim a file operation occurred
without a receipt. Propose risky changes for simulation and review; never silently execute
delete, shell, inline Python, overwrite, or escaping path operations."""

InputFn = Callable[[str], str]
OutputFn = Callable[[str], None]
SecretFn = Callable[[str], str]
FeedFn = Callable[..., dict[str, Any]]
AskFn = Callable[..., dict[str, Any]]
RecordFn = Callable[..., str]


@dataclass
class SessionState:
    model: str = DEFAULT_MODEL
    api_key: str | None = field(default=None, repr=False)
    authorization: dict[str, Any] | None = None
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def ready(self) -> bool:
        return bool(self.api_key and self.model and self.authorization)


def fusion_authorization(
    resident_identity: str,
    *,
    operator_approved: bool,
    guardian_approved: bool,
) -> dict[str, Any] | None:
    """Build Mantle's target-bound receipt only after both explicit decisions."""

    if not operator_approved or not guardian_approved:
        return None
    try:
        from mantle.core.authority import build_fusion_authorization
        return build_fusion_authorization(
            resident_identity,
            operator_approved=operator_approved,
            guardian_approved=guardian_approved,
        )
    except ImportError:
        # Standalone product tests may not have Mantle on sys.path; retain the
        # exact minimized shape as a compatibility fallback.
        return {
            "target": {"resident_identity": resident_identity},
            "operator": {"fusion_decision": "APPROVED"},
            "guardian": {"fusion_decision": "APPROVED"},
            "effective_decision": {"mind_fusion_authorized": True},
        }


def positive_credits(value: str) -> float:
    credits = float(value)
    if not 0 < credits <= 100_000:
        raise ValueError("credits must be greater than 0 and no more than 100000")
    return credits


def _yes(value: str) -> bool:
    return value.strip().lower() in {"y", "yes"}


def normalize_model(value: str) -> str:
    selected = value.strip()
    if not selected or selected.lower() == "free":
        return DEFAULT_MODEL
    if selected.lower() == "auto":
        return "openrouter/auto"
    if not _MODEL_RE.fullmatch(selected):
        raise ValueError(
            "model must be a bounded provider/model identifier without whitespace"
        )
    return selected


class ResidentTerminal:
    def __init__(
        self,
        product_root: str | Path,
        *,
        input_fn: InputFn = input,
        secret_fn: SecretFn = getpass.getpass,
        output_fn: OutputFn = print,
        feed_fn: FeedFn | None = None,
        ask_fn: AskFn | None = None,
        record_fn: RecordFn | None = None,
    ) -> None:
        self.product_root = Path(product_root).resolve(strict=True)
        workspace = discover_workspace(self.product_root)
        if workspace is None:
            raise ValueError(
                "no self-consistent Organize.AppAI WORKSPACE.txt was found"
            )
        require_contained(workspace, self.product_root)
        if not (self.product_root / ".mantle" / "organism.json").is_file():
            raise ValueError(
                f"no resident Body found at {self.product_root / '.mantle'}"
            )
        self.workspace = workspace
        self.input = input_fn
        self.secret = secret_fn
        self.output = output_fn
        self._feed: FeedFn | None = feed_fn
        self._ask: AskFn | None = ask_fn
        self._record: RecordFn | None = record_fn
        self.state = SessionState()
        self._body_dispatcher = None
        self._resident_runtime = None
        self.last_provider_receipt: dict[str, Any] | None = None
        status = MantleBridge(self.product_root).status()
        identity = status.get("identity")
        self.identity = (
            str(identity.get("name"))
            if isinstance(identity, dict) and identity.get("name")
            else "Organize.AppAI"
        )

    def _dispatcher(self):
        """Load Mantle's canonical Body command dispatcher once.

        The product keeps host-only extensions (/credits and /authorize), while all
        universal slash commands use Mantle's typed command contract and receipts.
        A missing Mantle source is fail-open for deterministic Organize behavior.
        """
        if self._body_dispatcher is not None:
            return self._body_dispatcher
        try:
            bridge = MantleBridge(self.product_root)
            org = bridge.load()
            from mantle.resident.commands import BodyCommandDispatcher
            self._body_dispatcher = BodyCommandDispatcher(org)
            self._body_dispatcher.register(
                "/credits", "add local Mantle energy units", self._body_credits
            )
            self._body_dispatcher.register(
                "/authorize", "record fresh dual MIND fusion decisions", self._body_authorize
            )
            self._body_dispatcher.register(
                "/vitals", "show Organize resident status", self._body_vitals
            )
        except Exception:
            self._body_dispatcher = None
        return self._body_dispatcher

    def _runtime(self):
        if self._resident_runtime is None:
            from mantle.contracts import ResidentRuntime
            self._resident_runtime = ResidentRuntime(self._dispatcher())
        return self._resident_runtime

    def _dispatch_body(self, text: str, *, secret_input: str | None = None) -> bool:
        dispatcher = self._dispatcher()
        if dispatcher is None:
            return False
        result = dispatcher.dispatch(text, secret_input=secret_input)
        if result.message:
            self.output(result.message)
        if result.ok and result.command in {"/model", "/mind"}:
            self.state.model = dispatcher.state.model
        if result.ok and result.command == "/key":
            self.state.api_key = dispatcher.state.credential()
        if result.command == "/offline" and result.ok:
            self.state.api_key = None
            self.state.authorization = None
        if result.command == "/status" and result.ok:
            self.output(json.dumps(result.details, indent=2, sort_keys=True))
            # Add host certification/fingerprint context without changing the
            # shared Body command's deterministic receipt.
            self.status()
        if result.command == "/evidence" and result.ok:
            self.output(json.dumps(result.details, indent=2, sort_keys=True))
        return True

    def _body_credits(self, argument: str, _secret: str | None):
        from mantle.resident.commands import BodyCommandResult
        try:
            credits = positive_credits(argument)
            result = self._feed_call(credits)
        except (TypeError, ValueError) as error:
            return BodyCommandResult("/credits", False, "refused", str(error))
        return BodyCommandResult(
            "/credits", True, "executed",
            f"Mantle energy balance: {result['balance']:.1f} credits "
            "(OpenRouter billing is separate).",
            changed_fields=("mantle_energy",), details={"balance": result["balance"]},
        )

    def _body_authorize(self, _argument: str, _secret: str | None):
        from mantle.resident.commands import BodyCommandResult
        before = self.state.authorization
        approved = self.configure_authorization()
        return BodyCommandResult(
            "/authorize", approved, "executed" if approved else "refused",
            "MIND fusion authorization is active for this session."
            if approved else "MIND fusion authorization remains disabled.",
            changed_fields=("fusion_authorization",)
            if self.state.authorization != before else (),
        )

    def _body_vitals(self, _argument: str, _secret: str | None):
        from mantle.resident.commands import BodyCommandResult
        return BodyCommandResult(
            "/vitals", True, "executed", "Organize resident status is available.",
            details=MantleBridge(self.product_root).status(),
        )

    def _feed_call(self, credits: float) -> dict[str, Any]:
        if self._feed is None:
            from mantle.anchor import feed

            self._feed = feed
        return self._feed(
            str(self.product_root),
            credits,
            key_name="openrouter",
            note="resident terminal energy grant; no raw provider key stored",
        )

    def _ask_call(self, question: str, *, use_mind: bool, model=None) -> dict[str, Any]:
        if self._ask is None:
            from mantle.anchor import ask

            self._ask = ask
        return self._ask(
            str(self.product_root),
            question,
            use_mind=use_mind,
            model=model,
            cost_per_call=1.0,
            fusion_authorization=self.state.authorization,
        )

    def _record_command(
        self,
        text: str,
        *,
        status: str,
        ok: bool,
        changed_fields: tuple[str, ...] = (),
    ) -> None:
        if self._record is None:
            self._record = cast(
                RecordFn, MantleBridge(self.product_root).remember_body_command
            )
        self._record(
            text,
            status=status,
            ok=ok,
            changed_fields=changed_fields,
            public_state={
                "provider": "openrouter",
                "model": self.state.model,
                "credential_configured": self.state.api_key is not None,
                "credential_storage": "session-memory-only",
                "fusion_authorized": self.state.authorization is not None,
            },
        )

    def setup_key(self) -> bool:
        key = self.secret("OpenRouter API key (hidden; blank cancels): ").strip()
        if not key:
            self.output(
                "Key setup cancelled; the deterministic Body remains available."
            )
            return False
        if len(key) < 12 or any(character.isspace() for character in key):
            self.output("Refused: the key format is not plausible.")
            return False

        model = self.input(f"OpenRouter model [{DEFAULT_MODEL}]: ")
        try:
            selected_model = normalize_model(model)
        except ValueError as error:
            self.output(f"Model was not changed: {error}")
            return False
        if self._dispatch_body("/key", secret_input=key):
            self._dispatch_body("/model " + selected_model)
        self.state.api_key = key
        self.state.model = selected_model
        fingerprint = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
        self.output(
            "Key accepted into session memory only "
            f"(SHA-256 prefix {fingerprint}); it was not written to disk."
        )

        self.output(
            "The resident will use its existing Mantle energy. Add more later with "
            "/credits N; OpenRouter account billing is separate."
        )

        self.configure_authorization()
        return True

    def configure_authorization(self) -> bool:
        operator = _yes(
            self.input(
                f"Operator approval to fuse a MIND into {self.identity}? [y/N]: "
            )
        )
        guardian = _yes(
            self.input(
                "Guardian approval recorded independently for this same resident? [y/N]: "
            )
        )
        self.state.authorization = fusion_authorization(
            self.identity,
            operator_approved=operator,
            guardian_approved=guardian,
        )
        if self.state.authorization is None:
            self.output(
                "MIND fusion remains disabled; deterministic conversation still works."
            )
            return False
        self.output(
            "Target-bound operator and guardian approvals accepted for this session."
        )
        return True

    def add_credits(self, argument: str) -> bool:
        raw = argument.strip() or self.input("Mantle local energy credits: ").strip()
        try:
            credits = positive_credits(raw)
            result = self._feed_call(credits)
        except (TypeError, ValueError) as error:
            self.output(f"Credits were not added: {error}")
            return False
        self.output(
            f"Mantle energy balance: {result['balance']:.1f} credits "
            "(OpenRouter billing is separate)."
        )
        return True

    def status(self) -> None:
        status = MantleBridge(self.product_root).status()
        try:
            import mantle
            mantle_version = mantle.__version__
        except Exception:
            mantle_version = "unavailable"
        safe = {
            "resident": self.identity,
            "body": "available" if status.get("available") else "unavailable",
            "persisted_stage1_certified": status.get("persisted_stage1_certified"),
            "mind_session": "ready" if self.state.ready else "offline",
            "model": self.state.model,
            "requested_model": self.state.model,
            "resolved_model": (
                (self.last_provider_receipt or {}).get("resolved_model")
                or (self.last_provider_receipt or {}).get("response_model")
            ),
            "model_evidence": (
                "provider_usage_receipt" if self.last_provider_receipt else "not_requested"
            ),
            "mantle_version": mantle_version,
            "resident_protocol": status.get("resident_protocol"),
            "historical_certification_receipt": status.get(
                "historical_certification_receipt"
            ),
            "host_fingerprint": status.get("host_fingerprint"),
            "certification_stale": status.get("certification_stale"),
            "key_in_session_memory": self.state.api_key is not None,
            "current_runtime_authority": bool(status.get("available")),
        }
        self.output(json.dumps(safe, indent=2, sort_keys=True))

    def converse(self, question: str) -> None:
        if not self.state.ready:
            result = self._ask_call(question, use_mind=False)
            self.output(result["answer"])
            self.output(
                f"\n[offline Body; energy {result['balance']:.1f}. "
                "Use /key to configure OpenRouter for this session.]"
            )
            return

        from mantle.mind.transport import openrouter_model

        model = openrouter_model(
            self.state.api_key or "",
            self.state.model,
            system=SYSTEM_PROMPT,
            max_tokens=1_024,
            session_id=self.state.session_id,
            lane="interactive",
        )
        try:
            runtime = self._runtime()
            runtime.provider = model
            turn = runtime.turn(question)
            self.last_provider_receipt = turn.provider_receipt
        except Exception as error:  # noqa: BLE001 - provider failures degrade to Body
            self.output(
                f"OpenRouter call failed ({type(error).__name__}); using the deterministic Body."
            )
            result = self._ask_call(question, use_mind=False)
            self.output(result["answer"])
            self.output(f"\n[energy {result['balance']:.1f} · {result['state']}]")
            return
        self.output(turn.visible_output)
        status = MantleBridge(self.product_root).status()
        self.output(
            f"\n[resident protocol {status.get('resident_protocol', 'unknown')} · "
            "provider receipt recorded]"
        )

    def command(self, text: str) -> bool:
        from mantle.resident.protocol import classify_user_submit
        marker = classify_user_submit(text)
        command = str(marker["command"])
        argument = text.strip().partition(" ")[2]
        if command == "/key":
            if argument:
                self.output(
                    "Refused: type /key alone so the credential is entered hidden."
                )
                return True
            self.setup_key()
            return True
        if command == "/exit":
            text = "/quit"
            command = "/quit"
        try:
            handled = self._dispatch_body(text)
        except Exception as error:  # noqa: BLE001 - Body remains fail-open
            self.output(
                f"Mantle Body command failed ({type(error).__name__}); "
                "deterministic organize commands remain available."
            )
            handled = False
        if not handled:
            self.output(
                "Mantle 2 runtime is unavailable; deterministic organize commands remain available."
            )
        return command != "/quit"

    def run(self, *, setup_key: bool = False) -> None:
        self.output(BANNER.format(product=self.product_root))
        if setup_key:
            configured = self.setup_key()
            try:
                self._record_command(
                    "/key",
                    status="executed" if configured else "cancelled",
                    ok=configured,
                    changed_fields=(
                        ("credential", "model", "fusion_authorization")
                        if configured
                        else ()
                    ),
                )
            except Exception as error:  # noqa: BLE001 - terminal remains usable
                self.output(
                    "Body command receipt could not be recorded "
                    f"({type(error).__name__}); the terminal remains available."
                )
        while True:
            try:
                text = self.input("\nYou> ").strip()
            except (EOFError, KeyboardInterrupt):
                self.output("\nSession closed.")
                break
            if not text:
                continue
            if text.startswith("/"):
                if not self.command(text):
                    break
            else:
                self.converse(text)


BANNER = """Organize.AppAI resident terminal
Product: {product}

Plain text speaks to the resident. Slash commands are maintenance only.
The OpenRouter key remains in memory for this terminal session and is never written to disk.
Use /help for commands; /quit closes the session.
"""

HELP = """Commands:
  /key          securely prompt for an OpenRouter key, model, and approvals
  /credits N    add N local Mantle energy credits (not OpenRouter account funds)
  /model ID     select an OpenRouter model slug (default: openrouter/free)
  /mind ID      alias for /model (canonical Body command)
  /authorize    enter explicit operator and guardian fusion decisions
  /status       show bounded resident/session status
  /vitals       show Organize host/certification evidence
  /offline      clear the provider key from process memory
  /provider-test validate local provider state without a network call
  /evidence     show bounded, redacted Body evidence
  /help         show this help
  /quit         close the terminal

Do not type a key after /key; the following hidden prompt is the secret boundary.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="organize-appai-resident")
    parser.add_argument("--product-root", required=True)
    parser.add_argument("--setup-key", action="store_true")
    args = parser.parse_args(argv)
    try:
        ResidentTerminal(args.product_root).run(setup_key=args.setup_key)
    except Exception as error:  # noqa: BLE001 - keep the desktop terminal open and useful
        print(f"Resident terminal could not start: {type(error).__name__}: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
