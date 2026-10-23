"""Body-system contracts and executable provider binding registry."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any

from .effects import Capability, CapabilityRegistry

BINDING_STATES = {"BOUND", "HOST_BOUND", "UNAVAILABLE"}


@dataclass(frozen=True)
class ProviderBinding:
    capability: Capability
    source: str = "portable"


class SystemRegistry:
    """Bind declared SYSTEMS interfaces to executable providers without lying.

    ``SYSTEMS.json`` is the public contract.  Interfaces marked BOUND must have an
    implementation in this registry. HOST_BOUND interfaces are intentionally supplied
    by an embedding host. UNAVAILABLE interfaces are descriptive only and cannot be
    selected for execution.
    """

    def __init__(self, systems: dict):
        self.systems = validate_systems_contract(systems)
        self._declared = interface_index(self.systems)
        self._bindings: dict[str, ProviderBinding] = {}

    def bind(self, capability: Capability, *, source: str = "portable"):
        declared = self._declared.get(capability.name)
        if declared is None:
            raise ValueError(f"Provider binding is not declared in SYSTEMS.json: {capability.name}")
        if declared["binding"] != "BOUND":
            raise ValueError(f"Capability {capability.name} is not declared BOUND")
        if declared["effect"] != capability.effect or declared.get("authority") != capability.authority:
            raise ValueError(f"Provider binding contract mismatch for {capability.name}")
        if declared.get("provider") != capability.provider_id:
            raise ValueError(f"Provider id mismatch for {capability.name}")
        if capability.name in self._bindings:
            raise ValueError(f"Duplicate provider binding: {capability.name}")
        self._bindings[capability.name] = ProviderBinding(capability, source)

    def verify_bindings(self):
        missing = sorted(
            name for name, spec in self._declared.items()
            if spec["binding"] == "BOUND" and name not in self._bindings
        )
        if missing:
            raise ValueError("BOUND interfaces missing executable providers: " + ", ".join(missing))
        return {
            "schema": "mantle.system-binding-report/1",
            "result": "PASS",
            "bound": sorted(self._bindings),
            "host_bound": sorted(name for name, spec in self._declared.items() if spec["binding"] == "HOST_BOUND"),
            "unavailable": sorted(name for name, spec in self._declared.items() if spec["binding"] == "UNAVAILABLE"),
        }

    def capability_registry(self) -> CapabilityRegistry:
        self.verify_bindings()
        reg = CapabilityRegistry()
        for name in sorted(self._bindings):
            reg.register(self._bindings[name].capability)
        return reg

    def catalog(self):
        report = self.verify_bindings()
        return {
            **report,
            "interfaces": [
                {
                    "name": name,
                    "system": spec["system"],
                    "binding": spec["binding"],
                    "effect": spec["effect"],
                    "authority": spec.get("authority"),
                    "provider": spec.get("provider"),
                }
                for name, spec in sorted(self._declared.items())
            ],
        }


def interface_index(systems: dict) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for system in systems.get("systems", []):
        sid = system.get("id")
        for interface in system.get("interfaces", []):
            name = interface.get("name")
            if name in index:
                raise ValueError(f"Duplicate SYSTEMS interface: {name}")
            index[name] = {**interface, "system": sid}
    return index


def validate_systems_contract(value: dict) -> dict:
    if not isinstance(value, dict) or value.get("schema") != "cell.systems/2":
        raise ValueError("Invalid SYSTEMS schema")
    systems = value.get("systems")
    if not isinstance(systems, list) or not systems:
        raise ValueError("SYSTEMS must declare at least one Body system")
    seen_systems = set()
    seen_interfaces = set()
    for system in systems:
        if not isinstance(system, dict) or not isinstance(system.get("id"), str):
            raise ValueError("Invalid Body system")
        if system["id"] in seen_systems:
            raise ValueError("Duplicate Body system id")
        seen_systems.add(system["id"])
        interfaces = system.get("interfaces")
        if not isinstance(interfaces, list):
            raise ValueError("System interfaces must be a list")
        for interface in interfaces:
            if not isinstance(interface, dict):
                raise ValueError("Invalid interface declaration")
            name = interface.get("name")
            if not isinstance(name, str) or not name:
                raise ValueError("Interface name is required")
            if name in seen_interfaces:
                raise ValueError("Duplicate SYSTEMS interface: " + name)
            seen_interfaces.add(name)
            if interface.get("binding") not in BINDING_STATES:
                raise ValueError(f"Interface {name} must declare BOUND, HOST_BOUND, or UNAVAILABLE")
            if interface.get("effect") not in {"READ", "COMPUTE", "MUTATE", "PUBLISH", "EXTERNAL"}:
                raise ValueError(f"Invalid effect class for {name}")
            provider = interface.get("provider")
            if interface["binding"] == "BOUND" and (not isinstance(provider, str) or not provider):
                raise ValueError(f"BOUND interface {name} requires a provider id")
            if interface["binding"] == "HOST_BOUND" and provider != "host-bound":
                raise ValueError(f"HOST_BOUND interface {name} must use provider host-bound")
    return value
