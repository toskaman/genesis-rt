# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Provenance bindings for imported QNX evidence (§6).

A target/perf record is UNTRUSTED input until every binding below holds.
The gate calls these validators; anything unexplained caps the earned
tier instead of failing the host verdict (the host side may be genuinely
fine while the imported evidence is stale, foreign or forged).

Chain of custody (each link is checked, none is assumed):

    IR digest + machine id  →  generated sources  →  toolchain  →
    built binaries  →  staged (target-observed) binaries  →
    execution record + checks + transcripts  →  measurements  →  verdict

What this proves: the evidence hangs together and matches THESE
artifacts (accidental reuse across machines/builds/IRs fails loudly).
What it does NOT prove: anything against a malicious local operator
who can rewrite records AND recompute digests (no trust anchor on a
dev box). See docs/passport-threat-model.md for the honest boundary.
"""
from __future__ import annotations

import datetime
import math
from typing import Any

# v2 (multi-build): target/perf records carry a `build_set` attributing
# every staged executable that the primary build did not produce.
# v1 records stay readable; they keep their tier only when nothing extra
# was staged (see check_legacy_extras) -- never upgraded.
PROVENANCE_VERSION = 2
SUPPORTED_PROVENANCE_VERSIONS = (1, 2)

# Exact on-target matrix, in run order. Single source of truth:
# scripts/qnx_target.py refuses to verify when its TARGET_MATRIX drifts
# from this tuple, and the gate refuses behavior tiers otherwise.
EXPECTED_TARGET_CHECKS = (
    "target_info",
    "faultinject",
    "status_live",
    "limits_differ",
    "device_chain",
    "conv_chain",
    "estop_target",
    "target_perf",
    "controller_flow",
    "supervisor_respawn",
    "supervisor_giveup",
    "v2_transitions",
    "guard_crash",
    "cell_policy",
)

TARGET_PLATFORM = "qnx8_x86_64_qemu"

# Clock-skew tolerance for imported timestamps (generous: QEMU guests
# drift; the check targets incoherence, not NTP discipline).
_FUTURE_SKEW_S = 3600


def _cksum_table() -> list[int]:
    poly = 0x04C11DB7
    tab = []
    for i in range(256):
        crc = i << 24
        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) ^ poly) & 0xFFFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFFFF
        tab.append(crc)
    return tab


_CKSUM_TABLE = _cksum_table()


def cksum_posix(data: bytes) -> tuple[int, int]:
    """POSIX cksum (CRC32 variant) + size, matching `cksum` on the target.

    Used to bind staged target binaries to locally built ones. CRC32
    catches accidental mismatch reliably; deliberate collision is out of
    scope (threat model) — sha256 is recorded alongside for inspection.
    """
    crc = 0
    for byte in data:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ _CKSUM_TABLE[((crc >> 24) ^ byte) & 0xFF]
    length = len(data)
    n = length
    while n:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ _CKSUM_TABLE[((crc >> 24) ^ (n & 0xFF)) & 0xFF]
        n >>= 8
    return (~crc) & 0xFFFFFFFF, length


def perf_distribution(samples: list[float]) -> dict[str, Any]:
    """Nearest-rank distribution (documented method, no interpolation)."""
    ordered = sorted(samples)
    n = len(ordered)

    def rank(p: float) -> float:
        return ordered[max(0, min(n - 1, math.ceil(p / 100.0 * n) - 1))]

    return {"count": n, "unit": "microseconds",
            "min": ordered[0], "max": ordered[-1],
            "p50": rank(50), "p95": rank(95), "p99": rank(99)}


def _parse_utc(value: Any) -> datetime.datetime | None:
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt is None or dt.tzinfo is None:
        return None
    return dt.astimezone(datetime.timezone.utc)


def check_window(started: Any, finished: Any,
                 now: datetime.datetime | None = None) -> list[str]:
    """Timestamp coherence: parseable, ordered, not from the future."""
    t0, t1 = _parse_utc(started), _parse_utc(finished)
    if t0 is None:
        return [f"unparsable started_utc: {started!r}"]
    if t1 is None:
        return [f"unparsable finished_utc: {finished!r}"]
    if not t0 < t1:
        return [f"incoherent window: finished_utc ({finished}) "
                f"not after started_utc ({started})"]
    now = now or datetime.datetime.now(datetime.timezone.utc)
    if (t1 - now).total_seconds() > _FUTURE_SKEW_S:
        return [f"finished_utc ({finished}) is more than "
                f"{_FUTURE_SKEW_S}s in the future"]
    return []


def check_target_identity(target: Any) -> list[str]:
    if not isinstance(target, dict):
        return [f"target identity missing (want platform={TARGET_PLATFORM!r})"]
    reasons = []
    if target.get("platform") != TARGET_PLATFORM:
        reasons.append(f"target platform {target.get('platform')!r} "
                       f"(want {TARGET_PLATFORM!r})")
    uname = target.get("uname", "")
    if not isinstance(uname, str) or "QNX" not in uname or "x86_64" not in uname:
        reasons.append("target uname does not identify QNX x86_64")
    return reasons


def check_staged_binaries(staged: Any, build_binaries: Any) -> list[str]:
    """Every binary THIS pipeline built must be staged with identical
    cksum+size. Extra staged binaries are attributed separately
    (provenance v2 build set, or refused for v1 by check_legacy_extras)."""
    if not isinstance(staged, dict) or not staged:
        return ["staged binaries missing (no target-observed cksums)"]
    if not isinstance(build_binaries, dict) or not build_binaries:
        return ["build binaries missing (legacy qnx_build without digests)"]
    reasons = []
    for name, built in build_binaries.items():
        obs = staged.get(name)
        if not isinstance(obs, dict):
            reasons.append(f"built binary {name} not found among staged")
            continue
        want_ck = built.get("cksum") if isinstance(built, dict) else None
        want_sz = built.get("size") if isinstance(built, dict) else None
        if obs.get("cksum") != want_ck or obs.get("size") != want_sz:
            reasons.append(
                f"staged binary {name} differs from this build "
                f"(cksum {obs.get('cksum')}/{want_ck}, "
                f"size {obs.get('size')}/{want_sz})")
    return reasons


def check_legacy_extras(staged: Any, build_binaries: Any) -> list[str]:
    """Provenance v1 had no build set: any executable staged beside the
    primary build is unattributed, so the record cannot earn a behavior
    tier. Records with nothing extra keep working unchanged."""
    if not isinstance(staged, dict) or not isinstance(build_binaries, dict):
        return []
    extra = sorted(n for n in staged if n not in build_binaries)
    if not extra:
        return []
    return [f"provenance v1 record stages {len(extra)} executable(s) from other "
            f"builds without attribution: {extra} (re-run verify with "
            f"--build-set to bind them; legacy evidence is never upgraded)"]


def _attribution(body: dict[str, Any], *, ir_body: dict[str, Any],
                 build_body: dict[str, Any]) -> list[str]:
    from . import buildset  # local: buildset imports evidence/codegen
    staged = body.get("staged")
    if body.get("provenance_version") == 1:
        return check_legacy_extras(staged, build_body.get("binaries"))
    ir_sha = ir_body.get("ir_sha256")
    primary_id = (buildset.build_id(build_body, ir_sha)
                  if isinstance(ir_sha, str) and build_body.get("binaries") else None)
    return buildset.check_build_set(
        staged=staged, primary_binaries=build_body.get("binaries"),
        primary_ir_sha256=ir_sha, primary_build_id=primary_id,
        build_set=body.get("build_set"), matrix=body.get("matrix"))


def validate_target_binding(*, ir_body: dict[str, Any],
                            build_body: dict[str, Any],
                            target_body: dict[str, Any]) -> list[str]:
    """Reasons the target record is NOT bound to this run ([] = bound)."""
    if target_body.get("provenance_version") not in SUPPORTED_PROVENANCE_VERSIONS:
        return [f"target record provenance_version "
                f"{target_body.get('provenance_version')!r} "
                f"(want {PROVENANCE_VERSION}; re-run verify to bind)"]
    reasons: list[str] = []
    matrix = target_body.get("matrix")
    if list(matrix or []) != list(EXPECTED_TARGET_CHECKS):
        missing = [n for n in EXPECTED_TARGET_CHECKS if n not in (matrix or [])]
        extra = [n for n in (matrix or []) if n not in EXPECTED_TARGET_CHECKS]
        reasons.append(f"matrix mismatch: missing={missing} extra={extra} "
                       f"(want all {len(EXPECTED_TARGET_CHECKS)} steps)")
    check_names = [c.get("name") for c in target_body.get("checks", [])
                   if isinstance(c, dict)]
    if check_names != list(matrix or []):
        reasons.append("checks do not match the declared matrix step list")
    reasons.extend(check_window(target_body.get("started_utc"),
                                target_body.get("finished_utc")))
    reasons.extend(check_target_identity(target_body.get("target")))
    att = target_body.get("ir")
    if not isinstance(att, dict):
        reasons.append("target record not bound to an IR "
                       "(re-run verify --ir)")
    else:
        if att.get("machine_id") != ir_body.get("machine", {}).get("id"):
            reasons.append(
                f"machine mismatch: record binds {att.get('machine_id')!r}, "
                f"passport IR is {ir_body.get('machine', {}).get('id')!r}")
        if att.get("ir_sha256") != ir_body.get("ir_sha256"):
            reasons.append("ir_sha256 mismatch: record was captured against "
                           "a different IR (stale evidence)")
    reasons.extend(check_staged_binaries(target_body.get("staged"),
                                         build_body.get("binaries")))
    reasons.extend(_attribution(target_body, ir_body=ir_body, build_body=build_body))
    transcripts = target_body.get("transcripts")
    if not isinstance(transcripts, dict):
        reasons.append("transcript digests missing (re-run verify)")
    else:
        for name in EXPECTED_TARGET_CHECKS:
            digest = transcripts.get(name)
            if (not isinstance(digest, str) or len(digest) != 64
                    or any(c not in "0123456789abcdef" for c in digest)):
                reasons.append(f"transcript digest missing/invalid for {name}")
    return reasons


def validate_perf_binding(*, build_body: dict[str, Any],
                          target_body: dict[str, Any],
                          perf_body: dict[str, Any],
                          ir_body: dict[str, Any] | None = None) -> list[str]:
    """Reasons the perf record is NOT bound ([] = bound)."""
    if perf_body.get("provenance_version") not in SUPPORTED_PROVENANCE_VERSIONS:
        return [f"perf record provenance_version "
                f"{perf_body.get('provenance_version')!r} "
                f"(want {PROVENANCE_VERSION}; re-run perf to bind)"]
    reasons: list[str] = []
    reasons.extend(check_window(perf_body.get("started_utc"),
                                perf_body.get("finished_utc")))
    reasons.extend(check_target_identity(perf_body.get("target")))
    samples = perf_body.get("raw_samples_us")
    if (not isinstance(samples, list) or not samples
            or not all(isinstance(s, (int, float)) and math.isfinite(s)
                       and s >= 0 for s in samples)):
        reasons.append("raw_samples_us missing/empty/non-finite "
                       "(measurements without samples prove nothing)")
        samples = None
    dist = (perf_body.get("measurements") or {}).get("ipc_roundtrip_us")
    if not isinstance(dist, dict):
        reasons.append("measurements.ipc_roundtrip_us missing")
    elif samples is not None:
        if dist.get("count") != len(samples):
            reasons.append(f"sample count {dist.get('count')} != "
                           f"{len(samples)} raw samples")
        else:
            expect = perf_distribution([float(s) for s in samples])
            bad = [k for k in ("min", "p50", "p95", "p99", "max")
                   if dist.get(k) != expect[k]]
            if bad:
                reasons.append(
                    f"perf distribution mismatch on {bad}: claimed values "
                    f"do not recompute from raw samples")
    reasons.extend(check_staged_binaries(perf_body.get("staged"),
                                         build_body.get("binaries")))
    if perf_body.get("provenance_version") == 1:
        reasons.extend(check_legacy_extras(perf_body.get("staged"),
                                           build_body.get("binaries")))
    elif perf_body.get("build_set") != target_body.get("build_set"):
        reasons.append("perf build set differs from the verified matrix run "
                       "(executables attributed to other builds)")
    tstaged, pstaged = target_body.get("staged"), perf_body.get("staged")
    if (isinstance(tstaged, dict) and isinstance(pstaged, dict)
            and tstaged != pstaged):
        reasons.append("perf staged binaries differ from the verified "
                       "matrix run (bench ran against other binaries)")
    return reasons
