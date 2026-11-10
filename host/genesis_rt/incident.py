# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Causal intake: validated incident documents (step 1 of the slice).

An incident is a small JSON document describing an observed failure:
which machine IR is affected and which observations were recorded.
Intake is fail-closed and bounded: unknown schema versions, bad ids,
and unknown observation kinds are rejected, never coerced. The intake
layer never executes anything; it only validates and digests.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .orchestrator import valid_run_id

INCIDENT_SCHEMA_VERSION = 1

#: Room for derived run-id suffixes inside the 64-char run id cap.
MAX_INCIDENT_ID_LEN = 48

#: Bounded observation vocabulary (directive §15: no arbitrary intake).
OBSERVED_KINDS = frozenset(
    {"symptom", "log_excerpt", "transcript_ref", "pack_ref",
     "measurement"}
)

_REQUIRED = ("schema_version", "incident_id", "title", "machine_ir",
             "observed")


class IncidentError(ValueError):
    """Incident file unreadable or structurally invalid."""


def valid_incident_id(incident_id: str) -> bool:
    """Same fail-closed rule as run ids (single segment, no traversal)."""
    return (isinstance(incident_id, str)
            and valid_run_id(incident_id)
            and len(incident_id) <= MAX_INCIDENT_ID_LEN)


def validate_incident(obj: Any) -> list[str]:
    """Return the list of findings; empty means valid. Never raises."""
    errs: list[str] = []
    if not isinstance(obj, dict):
        return ["incident must be a JSON object"]
    for key in _REQUIRED:
        if key not in obj:
            errs.append(f"missing required key: {key}")
    if errs:
        return errs
    if obj["schema_version"] != INCIDENT_SCHEMA_VERSION:
        errs.append("unsupported schema_version: "
                    f"{obj['schema_version']!r}")
    if not valid_incident_id(obj["incident_id"]):
        errs.append(f"invalid incident_id: {obj['incident_id']!r} "
                    "(ASCII alnum, '-', '_' only, 1..48 chars)")
    if (not isinstance(obj["title"], str)) or (not obj["title"].strip()):
        errs.append("title must be a non-empty string")
    if (not isinstance(obj["machine_ir"], str)) or (
            not obj["machine_ir"].strip()):
        errs.append("machine_ir must be a non-empty path string")
    observed = obj["observed"]
    if not isinstance(observed, list) or not observed:
        errs.append("observed must be a non-empty list")
        return errs
    for i, item in enumerate(observed):
        if not isinstance(item, dict):
            errs.append(f"observed[{i}] must be an object")
            continue
        for key in ("kind", "detail", "source"):
            if not isinstance(item.get(key), str) or (
                    not item[key].strip()):
                errs.append(f"observed[{i}].{key} must be a "
                            "non-empty string")
        kind = item.get("kind")
        if (isinstance(kind, str) and kind.strip()
                and kind not in OBSERVED_KINDS):
            errs.append(f"observed[{i}].kind unknown: {kind!r} "
                        f"(allowed: {sorted(OBSERVED_KINDS)})")
    return errs


def load_incident(path: str | Path) -> dict[str, Any]:
    """Read + validate an incident file. Raises IncidentError."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise IncidentError(f"cannot load incident {path}: {exc}") from exc
    errs = validate_incident(raw)
    if errs:
        raise IncidentError(f"invalid incident {path}: {errs[0]}")
    return raw


def incident_digest(obj: dict[str, Any]) -> str:
    """Stable sha256 over canonical JSON (key order/whitespace free)."""
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
