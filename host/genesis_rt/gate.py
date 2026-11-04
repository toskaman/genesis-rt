# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Release gate: fail-closed verdict over an evidence passport.

PASS requires ALL of: valid hash chain, every required scenario
present with status "pass", a qnx_build record present (its own
qnx_verified flag is reported separately and never conflated with
the host verdict), and no failed/crashed records among required
scenarios. Anything else => FAIL with explicit reasons.
"""

from __future__ import annotations

import datetime
from typing import Any

from .evidence import verify_chain


def evaluate(passport: dict[str, Any], required_scenarios: list[str]) -> dict[str, Any]:
    reasons: list[str] = []
    chain = passport.get("chain", [])

    chain_errors = verify_chain(passport)
    if chain_errors:
        reasons.extend(f"chain: {e}" for e in chain_errors)

    by_kind = {r.get("kind"): r for r in chain if isinstance(r, dict)}
    qnx_rec = by_kind.get("qnx_build")
    if qnx_rec is None:
        reasons.append("missing qnx_build record")
    tgt_rec = by_kind.get("qnx_target")
    qnx_verified = False
    if tgt_rec is not None:
        # qnx_verified is reported alongside the host verdict, never gating it:
        # a missing target record keeps qnx_verified=false without failing.
        body = tgt_rec.get("body", {})
        checks = body.get("checks", [])
        if (body.get("status") == "ok"
                and body.get("verified_on_target") is True
                and isinstance(checks, list) and len(checks) > 0
                and all(c.get("passed") is True for c in checks)):
            qnx_verified = True

    missing: list[str] = []
    failed: list[str] = []
    for name in required_scenarios:
        rec = by_kind.get(f"scenario:{name}")
        if rec is None:
            missing.append(name)
            continue
        status = rec.get("body", {}).get("status")
        if status != "pass":
            failed.append(f"{name}={status}")
    if missing:
        reasons.append(f"missing scenario records: {sorted(missing)}")
    if failed:
        reasons.append(f"non-pass scenarios: {sorted(failed)}")
    if not required_scenarios:
        reasons.append("no required scenarios declared (refusing vacuous pass)")

    verdict = "FAIL" if reasons else "PASS"
    return {
        "verdict": verdict,
        "reasons": reasons,
        "required": sorted(required_scenarios),
        "missing": sorted(missing),
        "failed": sorted(failed),
        "qnx_verified": qnx_verified,
        "evaluated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }
