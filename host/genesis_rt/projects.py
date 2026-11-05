# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Studio Live project store: server-side Machine IR revisions.

Each project is a directory ``<root>/<pid>/`` with ``meta.json`` plus one
``rev-<n>.json`` per saved revision (validated, normalized IR). The store
lives under ``artifacts/studio/projects`` (git-ignored): user work never
enters the repository. All writes are atomic (tmp file + os.replace) and
confined under the store root; names, ids and payload sizes are capped.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from .codegen import ir_sha256 as ir_sha256_v1
from .ir import IRValidationError, validate_ir

MAX_IR_BYTES = 256 * 1024
MAX_REVISIONS = 200
MAX_DIFF_ENTRIES = 200

_PID_RE = re.compile(r"prj-[0-9a-f]{12}")
_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 _.\-]{0,63}")

_lock = threading.Lock()


class ProjectNotFound(Exception):
    """No project (or revision) with that id."""


class ProjectFull(Exception):
    """Revision history exhausted (MAX_REVISIONS saved)."""


def valid_project_id(pid: str) -> bool:
    return isinstance(pid, str) and _PID_RE.fullmatch(pid) is not None


def valid_name(name: str) -> bool:
    return isinstance(name, str) and _NAME_RE.fullmatch(name) is not None


def validate_any(doc: Any) -> tuple[int, dict[str, Any]]:
    """Version-aware dispatch: validate v1 or v2, never downgrade.

    Returns (schema_version, normalized_ir). Raises IRValidationError.
    """
    from .ir_v2 import validate_v2

    version = doc.get("schema_version") if isinstance(doc, dict) else None
    if version == 2:
        return 2, validate_v2(doc)
    if version == 1:
        return 1, validate_ir(doc)
    raise IRValidationError(f"unsupported schema_version={version!r}")


def summarize(version: int, ir: dict[str, Any]) -> dict[str, Any]:
    """Small Designer-facing digest of a validated IR (no raw echo)."""
    machine = ir.get("machine", {}) if isinstance(ir, dict) else {}
    verification = ir.get("verification", {}) if isinstance(ir, dict) else {}
    scenarios = verification.get("scenarios", []) if isinstance(verification, dict) else []
    sensors = ir.get("sensors", []) or []
    actuators = ir.get("actuators", []) or []
    contracts = ir.get("safety_contracts", []) or []
    out: dict[str, Any] = {
        "schema_version": version,
        "machine": {
            "id": machine.get("id"),
            "kind": machine.get("kind"),
            "execution_target": machine.get("execution_target"),
            "simulation_only": machine.get("simulation_only"),
        },
        "control": ir.get("control", {}),
        "counts": {
            "sensors": len(sensors),
            "actuators": len(actuators),
            "scenarios": len(scenarios),
            "contracts": len(contracts),
        },
        "scenarios": list(scenarios),
        "sensors": [{"id": s.get("id"), "type": s.get("type"),
                     "freshness_limit_ms": s.get("freshness_limit_ms")}
                    for s in sensors if isinstance(s, dict)],
        "actuators": [{"id": a.get("id"), "type": a.get("type")}
                      for a in actuators if isinstance(a, dict)],
        "contracts": [c.get("name") for c in contracts if isinstance(c, dict)],
        "ir_sha256": ir_sha256_v1(ir),
    }
    if version == 2:
        states = ir.get("states", []) or []
        transitions = ir.get("transitions", []) or []
        out["counts"]["states"] = len(states)
        out["counts"]["transitions"] = len(transitions)
        out["states"] = states
        out["transitions"] = transitions
        fault_responses = ir.get("fault_responses", []) or []
        out["fault_responses"] = [
            f.get("fault") if isinstance(f, dict) else f for f in fault_responses]
    return out


def ir_diff(a: Any, b: Any) -> dict[str, Any]:
    """Bounded structural diff of two JSON values.

    Returns {"changed": [{path, kind, before, after}], "truncated": bool}
    with JSON-path-ish ``a.b[0].c`` paths. Order of dict keys is
    normalized (sorted) so key order never reports as a change.
    """
    changed: list[dict[str, Any]] = []
    truncated = False

    def _cap(value: Any) -> Any:
        text = json.dumps(value, sort_keys=True, ensure_ascii=True,
                          default=str)
        if len(text) > 200:
            return text[:200] + "…(truncated)"
        return value

    def _walk(x: Any, y: Any, path: str) -> None:
        nonlocal truncated
        if len(changed) >= MAX_DIFF_ENTRIES:
            truncated = True
            return
        if isinstance(x, dict) and isinstance(y, dict):
            for key in sorted(set(x) | set(y)):
                if len(changed) >= MAX_DIFF_ENTRIES:
                    truncated = True
                    return
                sub = f"{path}.{key}" if path else str(key)
                if key not in x:
                    changed.append({"path": sub, "kind": "added",
                                    "before": None, "after": _cap(y[key])})
                elif key not in y:
                    changed.append({"path": sub, "kind": "removed",
                                    "before": _cap(x[key]), "after": None})
                else:
                    _walk(x[key], y[key], sub)
            return
        if isinstance(x, list) and isinstance(y, list):
            if len(x) != len(y):
                changed.append({"path": path or "$", "kind": "changed",
                                "before": f"list[{len(x)}]",
                                "after": f"list[{len(y)}]"})
            for i, (xe, ye) in enumerate(zip(x, y)):
                _walk(xe, ye, f"{path}[{i}]")
                if truncated:
                    return
            return
        if x != y or type(x) is not type(y):
            changed.append({"path": path or "$", "kind": "changed",
                            "before": _cap(x), "after": _cap(y)})

    _walk(a, b, "")
    return {"changed": changed, "truncated": truncated}


class ProjectStore:
    """Filesystem-backed project revisions rooted at ``root``."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    # -- internal ---------------------------------------------------
    def _dir(self, pid: str) -> Path:
        if not valid_project_id(pid):
            raise ProjectNotFound(pid)
        candidate = (self.root / pid).resolve()
        base = self.root.resolve()
        if base not in candidate.parents:
            raise ProjectNotFound(pid)
        return candidate

    def _meta(self, pid: str) -> dict[str, Any]:
        try:
            return json.loads((self._dir(pid) / "meta.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ProjectNotFound(pid) from exc

    def _write(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.parent / f".{path.name}.{os.getpid()}.tmp"
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, path)

    def _revision_path(self, pid: str, rev: int) -> Path:
        return self._dir(pid) / f"rev-{rev}.json"

    def _load_revision(self, pid: str, rev: int) -> dict[str, Any]:
        try:
            return json.loads(self._revision_path(pid, rev).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ProjectNotFound(f"{pid} rev {rev}") from exc

    # -- API ---------------------------------------------------------
    def create(self, name: str, ir: dict[str, Any]) -> dict[str, Any]:
        if not valid_name(name):
            raise ValueError(f"invalid project name: {name!r}")
        raw = json.dumps(ir).encode("utf-8")
        if len(raw) > MAX_IR_BYTES:
            raise ValueError(f"IR payload too large ({len(raw)} bytes)")
        version, valid = validate_any(ir)  # raises IRValidationError
        pid = f"prj-{uuid.uuid4().hex[:12]}"
        now = time.time()
        with _lock:
            self._write(self._dir(pid) / "meta.json",
                        {"pid": pid, "name": name, "head": 1,
                         "created": now, "updated": now})
            self._write(self._revision_path(pid, 1), valid)
        return {"pid": pid, "name": name, "head": 1,
                "summary": summarize(version, valid)}

    def list(self) -> list[dict[str, Any]]:
        out = []
        if not self.root.is_dir():
            return out
        for child in sorted(self.root.iterdir(), key=lambda p: p.name):
            if not valid_project_id(child.name):
                continue
            try:
                meta = self._meta(child.name)
                head_doc = self._load_revision(child.name, int(meta["head"]))
                version = 2 if head_doc.get("schema_version") == 2 else 1
                machine = head_doc.get("machine", {})
            except (ProjectNotFound, KeyError, ValueError):
                continue  # ignore half-written/corrupt entries, never crash list
            out.append({"pid": meta["pid"], "name": meta.get("name"),
                        "head": meta.get("head"), "updated": meta.get("updated"),
                        "schema_version": version,
                        "machine": machine.get("id"), "kind": machine.get("kind")})
        return out

    def get(self, pid: str) -> dict[str, Any]:
        meta = self._meta(pid)
        head = int(meta["head"])
        doc = self._load_revision(pid, head)
        version = 2 if doc.get("schema_version") == 2 else 1
        return {"pid": pid, "name": meta.get("name"), "head": head,
                "updated": meta.get("updated"), "ir": doc,
                "summary": summarize(version, doc)}

    def save_revision(self, pid: str, ir: dict[str, Any]) -> dict[str, Any]:
        raw = json.dumps(ir).encode("utf-8")
        if len(raw) > MAX_IR_BYTES:
            raise ValueError(f"IR payload too large ({len(raw)} bytes)")
        version, valid = validate_any(ir)  # raises IRValidationError
        with _lock:
            meta = self._meta(pid)
            head = int(meta["head"])
            current = self._load_revision(pid, head)
            if ir_sha256_v1(current) == ir_sha256_v1(valid):
                return {"pid": pid, "head": head, "unchanged": True,
                        "summary": summarize(version, valid)}
            if head >= MAX_REVISIONS:
                raise ProjectFull(f"{pid} already holds {MAX_REVISIONS} revisions")
            new_head = head + 1
            self._write(self._revision_path(pid, new_head), valid)
            meta["head"] = new_head
            meta["updated"] = time.time()
            self._write(self._dir(pid) / "meta.json", meta)
        return {"pid": pid, "head": new_head, "unchanged": False,
                "summary": summarize(version, valid)}

    def duplicate(self, pid: str, name: str) -> dict[str, Any]:
        current = self.get(pid)  # raises ProjectNotFound
        return self.create(name, current["ir"])

    def history(self, pid: str) -> list[dict[str, Any]]:
        meta = self._meta(pid)
        head = int(meta["head"])
        out = []
        for rev in range(1, head + 1):
            doc = self._load_revision(pid, rev)
            machine = doc.get("machine", {}) if isinstance(doc, dict) else {}
            out.append({"rev": rev, "ir_sha256": ir_sha256_v1(doc),
                        "machine": machine.get("id"),
                        "schema_version": doc.get("schema_version")})
        try:
            out[-1]["ts"] = meta.get("updated")
            out[0]["ts"] = meta.get("created")
        except IndexError:
            pass
        return out

    def revision(self, pid: str, rev: int) -> dict[str, Any]:
        meta = self._meta(pid)
        head = int(meta["head"])
        if not 1 <= rev <= head:
            raise ProjectNotFound(f"{pid} rev {rev}")
        doc = self._load_revision(pid, rev)
        version = 2 if doc.get("schema_version") == 2 else 1
        return {"pid": pid, "rev": rev, "ir": doc,
                "summary": summarize(version, doc)}

    def diff(self, pid: str, rev_a: int, rev_b: int) -> dict[str, Any]:
        ra = self.revision(pid, rev_a)  # range-checked
        rb = self.revision(pid, rev_b)
        result = ir_diff(ra["ir"], rb["ir"])
        result["from"] = rev_a
        result["to"] = rev_b
        return result

    def export(self, pid: str) -> dict[str, Any]:
        meta = self._meta(pid)
        head = int(meta["head"])
        doc = self._load_revision(pid, head)
        return {"project": {"pid": pid, "name": meta.get("name"),
                            "head": head, "exported": time.time()},
                "ir": doc}
