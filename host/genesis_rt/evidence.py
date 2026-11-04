# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Evidence passport: hash-linked, machine-readable verification record.

Chain rule: record.hash = sha256(canonical(body) + prev_hash).
Wall-clock timestamps live in the envelope only and are excluded from
hashes, so identical runs produce identical chains.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import platform
import subprocess
from pathlib import Path
from typing import Any

from . import __version__
from .ir import canonical_json

PASSPORT_VERSION = 1
GENESIS_PREV = "GENESIS" + "0" * 57  # 64-char genesis previous-hash


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _git_commit(repo: str | Path | None = None) -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            capture_output=True, text=True, timeout=10,
            cwd=str(repo) if repo else None, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


def environment_manifest(qnx: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "genesis_version": __version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "git_commit": _git_commit(Path(__file__).resolve().parent.parent.parent),
        "qnx": qnx or {"sdk_present": False, "status": "not_probed"},
    }


def _chain_append(chain: list[dict[str, Any]], kind: str, body: dict[str, Any]) -> dict[str, Any]:
    prev = chain[-1]["hash"] if chain else GENESIS_PREV
    digest = _sha256_hex((canonical_json(body) + prev).encode("utf-8"))
    record = {"seq": len(chain), "kind": kind, "body": body,
              "prev_hash": prev, "hash": digest}
    chain.append(record)
    return record


def _slim_trace(trace: list[dict[str, Any]], limit: int = 40) -> dict[str, Any]:
    """Store head/tail of a trace plus its digest (bounded passport size)."""
    digest = _sha256_hex(canonical_json(trace).encode("utf-8"))
    if len(trace) <= limit:
        return {"digest": digest, "events": trace, "truncated": False}
    head = trace[: limit // 2]
    tail = trace[-(limit // 2):]
    return {"digest": digest, "events_head": head, "events_tail": tail,
            "event_count": len(trace), "truncated": True}


def build_passport(run_id: str, ir: dict[str, Any],
                   codegen_manifest: dict[str, Any],
                   scenario_results: list[dict[str, Any]],
                   qnx_build: dict[str, Any] | None = None) -> dict[str, Any]:
    chain: list[dict[str, Any]] = []
    _chain_append(chain, "ir", {"ir_sha256": codegen_manifest["ir_sha256"],
                                "machine": ir["machine"],
                                "scenarios": ir["verification"]["scenarios"]})
    _chain_append(chain, "codegen", codegen_manifest)
    _chain_append(chain, "qnx_build", qnx_build or {"status": "missing"})
    for res in scenario_results:
        body = {"scenario": res["scenario"], "seed": res["seed"],
                "status": res["status"], "checks": res.get("checks", []),
                "stats": res.get("stats", {}),
                "trace": _slim_trace(res.get("trace", []))}
        _chain_append(chain, f"scenario:{res['scenario']}", body)
    passed = sum(1 for r in scenario_results if r["status"] == "pass")
    failed = sum(1 for r in scenario_results if r["status"] not in ("pass",))
    _chain_append(chain, "summary",
                  {"scenarios_total": len(scenario_results),
                   "scenarios_passed": passed, "scenarios_failed": failed})
    return {
        "passport_version": PASSPORT_VERSION,
        "run_id": run_id,
        "created_utc": _utc_now(),
        "environment": environment_manifest(qnx_build),
        "chain": chain,
    }


def attach_verdict(passport: dict[str, Any], verdict: dict[str, Any]) -> dict[str, Any]:
    body = {k: v for k, v in verdict.items() if k != "evaluated_utc"}
    _chain_append(passport["chain"], "gate_verdict", body)
    passport["gate"] = verdict.get("verdict", "UNKNOWN")
    return passport


def verify_chain(passport: dict[str, Any]) -> list[str]:
    """Recompute the hash chain. Returns a list of errors (empty => valid)."""
    errors: list[str] = []
    if passport.get("passport_version") != PASSPORT_VERSION:
        errors.append(f"unsupported passport_version: {passport.get('passport_version')!r}")
    chain = passport.get("chain", [])
    if not chain:
        return errors + ["empty chain"]
    prev = GENESIS_PREV
    for i, record in enumerate(chain):
        for key in ("seq", "kind", "body", "prev_hash", "hash"):
            if key not in record:
                errors.append(f"record {i}: missing {key}")
        if record.get("seq") != i:
            errors.append(f"record {i}: bad seq {record.get('seq')!r}")
        if record.get("prev_hash") != prev:
            errors.append(f"record {i}: prev_hash mismatch")
        expect = _sha256_hex((canonical_json(record.get("body", {})) + prev).encode("utf-8"))
        if record.get("hash") != expect:
            errors.append(f"record {i} ({record.get('kind')}): hash mismatch")
        prev = record.get("hash", "")
    return errors


def save_passport(passport: dict[str, Any], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(passport, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def load_passport(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "chain" not in data:
        raise ValueError("not a GENESIS evidence passport")
    return data
