"""Optional Body-owned rolling context and provider-cache architecture."""
from .canonical import canonical_json_bytes, render_entry, render_entries, sha256_hex
from .counter import CallableTokenCounter, ConservativeByteCounter, TokenCounter
from .ledger import (
    ContextLedger,
    context_band_boot,
    install_context_band,
)
from .strategy import (
    RollingPrefixContextStrategy,
    SnapshotContextStrategy,
    model_info_from_transport,
)
from .types import (
    CONTEXT_SCHEMA,
    RENDER_FORMAT,
    ContextBudgetExceeded,
    ContextCapabilityUnavailable,
    ContextIntegrityError,
    ContextKey,
    ContextMigrationRequired,
    ContextStrategy,
    ModelInfo,
    ModelRequest,
    ModelResponse,
    PreparedContext,
    ProviderCapabilities,
    RollingContextConfig,
    SourceCursor,
)

__all__ = [
    "CONTEXT_SCHEMA", "RENDER_FORMAT",
    "CallableTokenCounter", "ConservativeByteCounter", "TokenCounter",
    "ContextLedger", "context_band_boot", "install_context_band",
    "RollingPrefixContextStrategy", "SnapshotContextStrategy",
    "model_info_from_transport", "ContextBudgetExceeded",
    "ContextCapabilityUnavailable", "ContextIntegrityError", "ContextKey", "ContextMigrationRequired",
    "ContextStrategy", "ModelInfo", "ModelRequest", "ModelResponse",
    "PreparedContext", "ProviderCapabilities", "RollingContextConfig",
    "SourceCursor", "canonical_json_bytes", "render_entry",
    "render_entries", "sha256_hex",
]
