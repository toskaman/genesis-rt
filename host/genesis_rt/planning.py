# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Provider-independent planning interface with validated output.

AI (or any provider) may *propose* machine specifications, but every
proposal travels the same strict validation gate as offline input:
provider output is untrusted until ``validate_ir`` accepts it. Providers
can never override safety policy, bypass the gate, or mark tests passed
-- they only produce candidate IR.

Only the deterministic offline provider is bundled; no paid API and no
network are required. Third parties add a provider by implementing one
method (``propose_raw``) and registering it in ``PROVIDERS``; see
``docs/planning-eval.md``. Requests that demand unsafe, out-of-scope,
or prompt-injecting behavior are refused with a precise explanation.
"""

from __future__ import annotations

import re
from typing import Any, Protocol

from .ir import IRValidationError, validate_ir
from .planner import PlannerRejection
from .planner import propose as offline_propose

# Unsafe / out-of-scope request patterns (matched on the lowered text).
# Each maps to a precise refusal explanation shown to the requester.
_UNSAFE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"disable.{0,20}guard|guard.{0,20}disable|no guard|without guard",
     "disabling or removing the safety guard is not supported"),
    (r"ignore.{0,20}(safe|limit|instruct)|bypass.{0,20}(safe|guard|gate)",
     "bypassing safety policy, the guard, or the verification gate is not supported"),
    (r"no speed limit|unlimited speed|remove.{0,20}limit|without.{0,20}limit",
     "unbounded actuation is not supported; state a speed within (0, 10] m/s"),
    (r"real (hardware|robot|machine)|production (use|deploy)|deploy.{0,20}production",
     "only simulation-only machines are supported; real-hardware deployment is out of scope"),
    (r"simulation.{0,12}(off|false|disable)|no simul",
     "disabling simulation-only mode is not supported"),
    (r"weapon|explosive|surveillance target",
     "that use case is out of scope for this engineering tool"),
    (r"system prompt|jailbreak|ignore previous|do anything now",
     "prompt-injection style instructions are not followed"),
)


class PlanningProvider(Protocol):
    """One-method adapter: raw proposal for a request (untrusted output)."""

    name: str

    def propose_raw(self, request: str, machine_id: str) -> Any:
        ...


class OfflineProvider:
    """Deterministic bundled provider: keyword planner, no network."""

    name = "offline"

    def propose_raw(self, request: str, machine_id: str) -> Any:
        return offline_propose(request, machine_id=machine_id)


PROVIDERS: dict[str, type[OfflineProvider]] = {"offline": OfflineProvider}


def _refuse_unsafe(request: str) -> None:
    text = (request or "").lower()
    for pattern, explanation in _UNSAFE_PATTERNS:
        if re.search(pattern, text):
            raise PlannerRejection(f"unsafe or unsupported requirement: {explanation}")


def plan_machine(request: str, machine_id: str = "machine-01",
                 provider: str | PlanningProvider = "offline") -> dict[str, Any]:
    """Plan a machine through a provider; output strictly validated.

    Raises PlannerRejection for unsafe requests, unknown providers,
    provider failures, and proposals that fail IR validation.
    """
    if isinstance(provider, str):
        if provider not in PROVIDERS:
            raise PlannerRejection(
                f"unknown provider {provider!r}; available: {sorted(PROVIDERS)}")
        impl: PlanningProvider = PROVIDERS[provider]()
    else:
        impl = provider
    _refuse_unsafe(request)
    try:
        raw = impl.propose_raw(request, machine_id)
    except PlannerRejection:
        raise
    except Exception as exc:  # noqa: BLE001 - provider bugs must not escape raw
        raise PlannerRejection(f"provider {impl.name!r} failed: {exc}") from exc
    if not isinstance(raw, dict):
        raise PlannerRejection(
            f"provider {impl.name!r} returned a non-object proposal: "
            f"{type(raw).__name__}")
    try:
        return validate_ir(raw)
    except IRValidationError as exc:
        raise PlannerRejection(
            f"provider {impl.name!r} proposal rejected by IR validation: {exc}"
        ) from exc
