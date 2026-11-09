# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Audit recorded model-call counts against frozen consultation labels.

Reads a frozen dataset (`expect_consult` per case) and one or more
COMMITTED raw result files (`consults` per row). Never runs a
provider, never modifies inputs. Exit 0: this describes evidence;
enforcement for new evaluations lives in `scripts/eval_planner.py`.

  PYTHONPATH=host python scripts/audit_eval_consults.py \\
      --dataset planning_holdout_v8.json \\
      --results evals/results/2026-11-09-omega4-v8/qwen2.5-7b.json \\
                evals/results/2026-11-09-omega4-v8/llama3.1-8b.json \\
      --out /tmp/v8-consult-audit.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(dataset_path: Path, result_paths: list[Path]) -> dict:
    dataset_blob = dataset_path.read_bytes()
    cases = json.loads(dataset_blob.decode("utf-8"))["cases"]
    expected: dict[str, bool | None] = {
        c["id"]: c.get("expect_consult") for c in cases}
    report: dict = {
        "dataset": dataset_path.name,
        "dataset_sha256": hashlib.sha256(dataset_blob).hexdigest(),
        "providers": {},
    }
    by_case: dict[str, dict] = {}
    for rp in result_paths:
        rows = json.loads(rp.read_text(encoding="utf-8"))["cases"]
        name = rp.stem
        missing, unexpected, multi, short_ok, unlabeled = [], [], [], [], []
        for r in rows:
            cid, calls = r["id"], r.get("consults", 0)
            by_case.setdefault(cid, {})[name] = calls
            flag = expected.get(cid)
            if calls > 1:
                multi.append(cid)
            if flag is True and calls == 0:
                missing.append(cid)
                if r.get("passed"):
                    short_ok.append(cid)
            elif flag is False and calls > 0:
                unexpected.append(cid)
            elif flag is None and calls > 0:
                unlabeled.append(cid)
        exp_n = sum(1 for v in expected.values() if v is True)
        report["providers"][name] = {
            "raw_sha256": _sha256(rp),
            "expected_consults": exp_n,
            "actual_total_consults": sum(
                r.get("consults", 0) for r in rows),
            "fallback_cases": sum(
                1 for r in rows if r.get("consults", 0) > 0),
            "missing_consults": sorted(missing),
            "unexpected_consults": sorted(unexpected),
            "multi_call_cases": sorted(multi),
            "short_circuited_passed": sorted(short_ok),
            "unlabeled_with_calls": sorted(unlabeled),
        }
    report["cross_provider_consult_diffs"] = sorted(
        cid for cid, calls in by_case.items() if len(set(calls.values())) > 1)
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True,
                    help="evals/<name>.json with expect_consult labels")
    ap.add_argument("--results", nargs="+", required=True,
                    help="committed raw per-provider result JSONs")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rep = audit(REPO / "evals" / a.dataset,
                [Path(p) if Path(p).is_absolute() else REPO / p
                 for p in a.results])
    print(json.dumps(rep, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=2) + "\n",
                               encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
