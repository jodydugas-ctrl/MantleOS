"""mantle.mind -- the bounded MIND (Phase 2 only; Mantle OS).

NOTHING in mantle.core / mantle.vcw / mantle.organs imports this package: the import
direction IS the Phase-1 guarantee. The model is a pluggable transport (a callable);
the offline deterministic stub is the default; there is no vendor SDK anywhere.
"""
from .transport import (
    complete_model,
    stub_mind,
    openai_compatible_model,
    openrouter_model,
    load_keyfile,
)
from .containment import WRITE_SURFACE, guarded_write
from .mind import Mind, fuse
from .inner_voice import InnerVoice
from .port import MindPort, OperatorPort
from .runtime import AppAIRuntime
from .usage import normalize_usage, stable_session_id
from .context import (
    ContextBudgetExceeded,
    ContextCapabilityUnavailable,
    ContextIntegrityError,
    ContextKey,
    ContextMigrationRequired,
    ModelInfo,
    ModelRequest,
    ModelResponse,
    ProviderCapabilities,
    RollingContextConfig,
    RollingPrefixContextStrategy,
    SnapshotContextStrategy,
    context_band_boot,
    install_context_band,
)

__all__ = ["stub_mind", "complete_model", "openai_compatible_model", "openrouter_model",
           "load_keyfile",
           "WRITE_SURFACE", "guarded_write", "Mind", "fuse", "InnerVoice", "AppAIRuntime",
           "MindPort", "OperatorPort"]
__all__ += ["normalize_usage", "stable_session_id"]
__all__ += [
    "ContextBudgetExceeded", "ContextCapabilityUnavailable",
    "ContextIntegrityError", "ContextKey",
    "ContextMigrationRequired", "ModelInfo", "ModelRequest", "ModelResponse",
    "ProviderCapabilities", "RollingContextConfig",
    "RollingPrefixContextStrategy", "SnapshotContextStrategy",
    "context_band_boot", "install_context_band",
]
