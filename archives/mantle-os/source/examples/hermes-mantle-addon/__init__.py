"""Hermes Mantle Addon plugin registration."""

from functools import partial

from .mantle_addon.authority import Ed25519AuthorityProvider
from .mantle_addon.config import ResidentConfig
from .mantle_addon.runtime import OBSERVER_HOOKS, RuntimeRegistry
from .mantle_addon.transport import build_model
from .schemas import MANTLE_RECORD_DISCOVERY, MANTLE_STATUS
from .tools import mantle_record_discovery, mantle_status


def register(ctx):
    """Register bounded tools and profile-aware, fail-open resident observers."""

    def active_config() -> ResidentConfig:
        from hermes_cli.config import load_config

        return ResidentConfig.from_hermes_config(load_config())

    runtimes = RuntimeRegistry(
        profile_resolver=lambda: ctx.profile_name,
        config_resolver=active_config,
        model_factory=lambda: build_model(ctx.llm),
        authority_provider_factory=Ed25519AuthorityProvider.from_environment,
    )
    ctx.register_tool(
        name="mantle_status",
        toolset="mantle",
        schema=MANTLE_STATUS,
        handler=mantle_status,
        description="Report the bundled Mantle OS version and command surface.",
    )
    ctx.register_tool(
        name="mantle_record_discovery",
        toolset="mantle",
        schema=MANTLE_RECORD_DISCOVERY,
        handler=partial(mantle_record_discovery, runtime_provider=runtimes.current),
        description=(
            "Record one bounded, explicitly unverified discovery through the "
            "resident Body's Limbs control."
        ),
    )

    def mind_command(raw_args: str) -> str:
        prompt = raw_args.strip()
        if not prompt:
            return "Usage: /mind <prompt>"
        try:
            answer = runtimes.current().ask_mind(prompt)
        except (TypeError, ValueError) as exc:
            return f"AppAI MIND refused the prompt: {exc}"
        except Exception:
            return (
                "AppAI MIND is unavailable. Verify the active Hermes model and "
                "plugin configuration."
            )
        return f"AppAI MIND › {answer}"

    ctx.register_command(
        name="mind",
        handler=mind_command,
        description="Send one prompt to the resident AppAI MIND through Hermes.",
        args_hint="<prompt>",
    )
    for hook_name in OBSERVER_HOOKS:
        ctx.register_hook(hook_name, partial(runtimes.invoke, hook_name))
