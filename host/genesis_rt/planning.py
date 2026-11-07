# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Provider-independent planning interface with validated output.

AI (or any provider) may *propose* machine specifications, but every
proposal travels the same strict validation gate as offline input:
provider output is untrusted until ``validate_ir`` accepts it. Providers
can never override safety policy, bypass the gate, or mark tests passed
-- they only produce candidate IR.

The deterministic offline provider is the default; no paid API and no
network are required. An opt-in OpenAI-compatible ``llm`` provider exists
(env-configured, stdlib HTTP, 64 KiB cap) and is held to the same gate. Third parties add a provider by implementing one
method (``propose_raw``) and registering it in ``PROVIDERS``; see
``docs/planning-eval.md``. Requests that demand unsafe, out-of-scope,
or prompt-injecting behavior are refused with a precise explanation.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Protocol

from .ir import IRValidationError, validate_ir
from .planner import PlannerRejection
from .planner import propose as offline_propose

# Unsafe / out-of-scope request patterns (matched on the lowered text).
# Each maps to a precise refusal explanation shown to the requester.
# This is a courtesy pre-filter for clear explanations, NOT the safety
# boundary: a rephrased request can slip past a regex. The boundary is
# validate_ir (simulation_only, bounded limits, guards) plus the
# deterministic compiler and the fail-closed evidence gate.
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


# -- Optional LLM provider (TITAN wave 2) ---------------------------------
# Untrusted assistant -> structured proposal -> strict validate_ir -> the
# deterministic compiler. The LLM never sees evidence, never touches the
# release gate, and its output is discarded unless validate_ir accepts it.
LLM_MAX_RESPONSE_BYTES = 64 * 1024
LLM_TIMEOUT_S = 60
_LLM_SYSTEM = (
    "You draft GENESIS RT Machine IR (schema_version 1) as ONE JSON object and "
    "nothing else. Only simulation-only machines: machine.simulation_only must "
    "be true and execution_target 'qnx8_x86_64_qemu'. Never remove limits or "
    "guards. If the request is unsafe or ambiguous, return "
    '{"refusal": "<reason>"}. Use this example as the exact shape:\n')


class LLMProvider:
    """OpenAI-compatible chat-completions provider (opt-in, stdlib only).

    Configured only through the environment: GENESIS_AI_ENDPOINT (base URL,
    e.g. http://127.0.0.1:11434/v1 for a local Ollama), GENESIS_AI_MODEL,
    optional GENESIS_AI_API_KEY. The key is sent as a bearer header and is
    never logged or echoed in errors.
    """

    name = "llm"

    def __init__(self) -> None:
        self.endpoint = os.environ.get("GENESIS_AI_ENDPOINT", "").rstrip("/")
        self.model = os.environ.get("GENESIS_AI_MODEL", "")
        self._key = os.environ.get("GENESIS_AI_API_KEY", "")
        if not self.endpoint or not self.model:
            raise PlannerRejection(
                "llm provider not configured: set GENESIS_AI_ENDPOINT and "
                "GENESIS_AI_MODEL (the offline provider needs no setup)")
        if not re.match(r"^https?://", self.endpoint):
            raise PlannerRejection("GENESIS_AI_ENDPOINT must be an http(s) URL")

    def propose_raw(self, request: str, machine_id: str) -> Any:
        example = offline_propose("small AMR max speed 1.2", machine_id=machine_id)
        body = json.dumps({
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": _LLM_SYSTEM + json.dumps(example)},
                {"role": "user", "content":
                    f"machine_id: {machine_id}\nrequest: {request[:2000]}"},
            ],
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._key:
            headers["Authorization"] = "Bearer " + self._key
        req = urllib.request.Request(self.endpoint + "/chat/completions",
                                     data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=LLM_TIMEOUT_S) as resp:
                raw = resp.read(LLM_MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            raise PlannerRejection(f"llm endpoint returned HTTP {exc.code}") from None
        except (urllib.error.URLError, OSError) as exc:
            raise PlannerRejection(f"llm endpoint unreachable: {exc.__class__.__name__}") from None
        if len(raw) > LLM_MAX_RESPONSE_BYTES:
            raise PlannerRejection("llm response exceeds 64 KiB limit")
        try:
            content = json.loads(raw)["choices"][0]["message"]["content"]
            proposal = json.loads(content)
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise PlannerRejection(f"llm returned malformed output: {exc.__class__.__name__}") from None
        if isinstance(proposal, dict) and "refusal" in proposal:
            raise PlannerRejection(f"llm refused: {str(proposal['refusal'])[:200]}")
        if isinstance(proposal, dict):
            proposal.setdefault("machine", {})
            if isinstance(proposal["machine"], dict):
                proposal["machine"]["id"] = machine_id
        return proposal


PROVIDERS: dict[str, type[Any]] = {"offline": OfflineProvider, "llm": LLMProvider}


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
        _refuse_unsafe(request)
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
