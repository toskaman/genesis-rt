# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""One-click engineering dossier export for target ops (Wave 10 F6/Sprint B).

build_dossier_zip() bundles a COMPLETED-or-terminal target operation into a
portable ZIP: a self-contained report.html, a sha256 manifest, the raw
evidence files (LF-canonicalized, binaries excluded by allowlist, secrets
redacted), and offline VERIFY.md instructions.

Fail-closed display: anything unknown, missing, or failed is shown as such
in red/grey — the report can only show green when state==COMPLETED,
gate==PASS, qnx_verified is true, and the passport chain replays clean.
"""
from __future__ import annotations

import datetime
import hashlib
import html
import io
import json
import zipfile
from pathlib import Path
from typing import Any

from .evidence import verify_chain
from .target import TERMINAL_TARGET

DOSSIER_VERSION = 1
MAX_DOSSIER_BYTES = 25 * 1024 * 1024
MAX_DOSSIER_FILES = 200
MAX_DETAIL_CHARS = 300

# Allowlisted evidence, mirrored from scripts/build_evidence_pack.py (any
# drift must be deliberate: unknown files — e.g. staged target binaries —
# are never bundled).
_TOP_FILES = ("ir.json", "passport.json", "qemu-console.log",
              "qnx-build-record.json", "stage-manifest.json",
              "gen-manifest.json")
_SUBDIRS = (("target", "transcripts"), ("perf", "performance"))
_GEN_SUFFIXES = (".mk", ".h", ".c")

_SECRET_HINTS = ("password", "secret", "token", "credential", "private_key")


class DossierError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="seconds")


def _lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _redact(obj: Any, path: str, redacted: list[str]) -> Any:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, val in obj.items():
            p = f"{path}.{key}" if path else str(key)
            if any(h in str(key).lower() for h in _SECRET_HINTS):
                redacted.append(p)
                out[key] = "***REDACTED***"
            else:
                out[key] = _redact(val, p, redacted)
        return out
    if isinstance(obj, list):
        return [_redact(v, f"{path}[{i}]", redacted)
                for i, v in enumerate(obj)]
    return obj


def _load_json(data: bytes) -> dict[str, Any] | None:
    try:
        obj = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


def collect_op_files(ops_dir: Path, op_id: str,
                     artifacts_root: Path | None = None
                     ) -> tuple[dict[str, bytes], dict[str, Any], list[str]]:
    """Return (arcname -> bytes, op record, redacted key paths).

    Raises DossierError(404) for unknown ops, 409 for non-terminal ops,
    413 when caps are exceeded.
    """
    rec_p = ops_dir / f"{op_id}.json"
    work = ops_dir / op_id
    try:
        rec = json.loads(rec_p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise DossierError(404, f"unknown op {op_id}")
    if not isinstance(rec, dict) or not work.is_dir():
        raise DossierError(404, f"unknown op {op_id}")
    if rec.get("state") not in TERMINAL_TARGET:
        raise DossierError(409, f"op {op_id} is {rec.get('state')}, "
                                "not terminal; dossier needs a settled op")
    files: dict[str, bytes] = {}
    redacted: list[str] = []
    total = 0

    def _add(arcname: str, data: bytes) -> None:
        nonlocal total
        if len(files) >= MAX_DOSSIER_FILES:
            raise DossierError(413, "dossier file cap exceeded")
        total += len(data)
        if total > MAX_DOSSIER_BYTES:
            raise DossierError(413, "dossier size cap exceeded (25 MiB)")
        files[arcname] = data

    clean_rec = _redact(rec, "", redacted)
    _add("target-op.json", _lf(json.dumps(clean_rec, indent=1)
                               .encode("utf-8")))
    ev_p = ops_dir / f"{op_id}.events.jsonl"
    if ev_p.is_file():
        _add("op-events.jsonl", _lf(ev_p.read_bytes()))
    for name in _TOP_FILES:
        p = work / name
        if p.is_file():
            _add(name, _lf(p.read_bytes()))
    for src, dst in _SUBDIRS:
        for p in sorted((work / src).glob("*")) if (work / src).is_dir() \
                else []:
            if p.is_file():
                _add(f"{dst}/{p.name}", _lf(p.read_bytes()))
    for p in sorted((work / "gen").glob("*")) if (work / "gen").is_dir() \
            else []:
        if p.is_file() and p.suffix in _GEN_SUFFIXES:
            _add(f"sources/{p.name}", _lf(p.read_bytes()))
    bs_raw = (rec.get("params") or {}).get("build_set", "")
    if bs_raw:
        try:
            bs_p = Path(bs_raw)
            ok = bs_p.is_file() and (
                artifacts_root is None or artifacts_root.resolve()
                in bs_p.resolve().parents)
        except OSError:
            ok = False
        if ok:
            _add("build-set.json", _lf(bs_p.read_bytes()))
    return files, rec, redacted


def _esc(value: Any, limit: int = MAX_DETAIL_CHARS) -> str:
    text = "" if value is None else str(value)
    if len(text) > limit:
        text = text[:limit] + "…"
    return html.escape(text, quote=True)


def _machine_name(ir: dict[str, Any] | None) -> str:
    if not ir:
        return "unknown machine"
    mach = ir.get("machine")
    if isinstance(mach, dict):
        return str(mach.get("name", "unnamed machine"))
    return str(mach) if mach else "unnamed machine"


def assess_op(op_id: str, rec: dict[str, Any],
              files: dict[str, bytes]) -> dict[str, Any]:
    """Verdict + explanation inputs shared by the report and /decision.

    verdict is PASS only for COMPLETED + gate PASS + qnx_verified +
    a clean chain replay; anything else is FAIL or NOT VERIFIED.
    """
    passport = _load_json(files.get("passport.json", b"")) or {}
    ir = _load_json(files.get("ir.json", b""))
    target = _load_json(files.get("transcripts/qnx-target-record.json",
                                  b"")) or {}
    perf = _load_json(files.get("performance/qnx-perf-record.json",
                                b"")) or {}
    build = _load_json(files.get("qnx-build-record.json", b"")) or {}
    chain_errors = verify_chain(passport) if passport else ["missing passport"]
    gate = str(passport.get("gate", "UNKNOWN"))
    qnx_verified = bool((rec.get("artifacts") or {}).get("qnx_verified"))
    state = str(rec.get("state", "?"))
    if state == "COMPLETED" and gate == "PASS" and qnx_verified \
            and not chain_errors:
        verdict = "PASS"
    elif gate == "FAIL" or state in ("FAILED", "INTERRUPTED"):
        verdict = "FAIL"
    else:
        verdict = "NOT VERIFIED"

    checks = target.get("checks", []) if isinstance(target, dict) else []
    if not isinstance(checks, list):
        checks = []
    passed = [c for c in checks if isinstance(c, dict)]
    failed = [str(c.get("name", "?")) for c in passed if not c.get("passed")]
    samples = perf.get("raw_samples_us", []) \
        if isinstance(perf, dict) else []
    missing = [n for n in ("ir.json", "passport.json",
                           "transcripts/qnx-target-record.json",
                           "performance/qnx-perf-record.json",
                           "qnx-build-record.json")
               if n not in files]
    gate_body = {}
    for r in passport.get("chain", []):
        if isinstance(r, dict) and r.get("kind") == "gate_verdict" \
                and isinstance(r.get("body"), dict):
            gate_body = r["body"]
    return {
        "op_id": op_id,
        "verdict": verdict,
        "state": state,
        "gate": gate,
        # Old passports predate level/release_eligible; fall back to
        # the legacy tier key and to the gate itself.
        "gate_level": str(gate_body.get("level")
                          or gate_body.get("tier") or "?"),
        "release_eligible": bool(gate_body.get(
            "release_eligible", gate == "PASS")) and not chain_errors,
        "qnx_verified": qnx_verified,
        "machine": _machine_name(ir),
        "ir_digest": str(((rec.get("artifacts") or {}).get("ir_sha256")
                         or (target.get("ir") or {}).get("ir_sha256")
                         or "?")),
        "toolchain": " ".join(str(
            (build.get("environment") or {}).get("qcc_version") or "")
            .split())[:160],
        "matrix": {"passed": sum(1 for c in passed if c.get("passed")),
                   "total": len(passed), "failed": failed},
        "perf_samples": len(samples) if isinstance(samples, list) else 0,
        "missing_evidence": missing,
        "chain_errors": [str(e)[:200] for e in chain_errors],
        "why": _why_lines(verdict, state, gate, qnx_verified,
                           chain_errors, missing, failed),
    }


def _why_lines(verdict: str, state: str, gate: str, qnx_verified: bool,
               chain_errors: list[str], missing: list[str],
               failed: list[str]) -> list[str]:
    """One-sentence causes, deterministic order, no raw JSON needed."""
    if verdict == "PASS":
        return ["all gates green: COMPLETED + gate PASS + "
                "QNX-verified + clean replay"]
    lines = []
    if state != "COMPLETED":
        lines.append(f"op did not complete (state {state})")
    if gate != "PASS":
        lines.append(f"gate verdict is {gate}, not PASS")
    if not qnx_verified:
        lines.append("not QNX-verified (host-only or unverified target run)")
    if chain_errors:
        lines.append(f"evidence replay failed: {chain_errors[0]}"[:160])
    for name in missing:
        lines.append(f"missing evidence: {name}")
    for name in failed:
        lines.append(f"native check failed: {name}")
    return lines or ["unexplained non-pass (report this as a bug)"]


def compare_ops(ops_dir: Path, artifacts_root: Path | None,
                before_id: str, after_id: str) -> dict[str, Any]:
    """Side-by-side assessment of two terminal ops plus a diff summary.

    Raises DossierError (404/409/413) like the dossier builder when
    either side is missing, non-terminal or over caps.
    """
    sides = {}
    for key, oid in (("before", before_id), ("after", after_id)):
        files, rec, _red = collect_op_files(ops_dir, oid, artifacts_root)
        sides[key] = assess_op(oid, rec, files)
    b, a = sides["before"], sides["after"]
    bf = set(b["matrix"]["failed"])
    af = set(a["matrix"]["failed"])
    sides["diff"] = {
        "ir_changed": b["ir_digest"] != a["ir_digest"],
        "verdict_changed": b["verdict"] != a["verdict"],
        "gate_changed": b["gate"] != a["gate"],
        "release_changed": (b["release_eligible"] != a["release_eligible"]),
        "toolchain_changed": b["toolchain"] != a["toolchain"],
        "newly_failed": sorted(af - bf),
        "newly_passed": sorted(bf - af),
        "matrix_before": f'{b["matrix"]["passed"]}/{b["matrix"]["total"]}',
        "matrix_after": f'{a["matrix"]["passed"]}/{a["matrix"]["total"]}',
    }
    return sides


def render_report(op_id: str, rec: dict[str, Any], files: dict[str, bytes],
                  redacted: list[str]) -> tuple[str, str]:
    """Return (report.html, verdict) with verdict in PASS/FAIL/NOT VERIFIED."""
    a = assess_op(op_id, rec, files)
    verdict = a["verdict"]
    badge = {"PASS": "pass", "FAIL": "fail"}.get(verdict, "unknown")
    target = _load_json(files.get("transcripts/qnx-target-record.json",
                                  b"")) or {}
    checks = target.get("checks", []) if isinstance(target, dict) else []
    if not isinstance(checks, list):
        checks = []
    n_pass = a["matrix"]["passed"]
    rows = []
    for c in checks:
        if not isinstance(c, dict):
            continue
        ok = bool(c.get("passed"))
        rows.append(
            f'<tr><td>{_esc(c.get("name", "?"), 80)}</td>'
            f'<td class="{"pass" if ok else "fail"}">'
            f'{"PASS" if ok else "FAIL"}</td>'
            f'<td>{_esc(c.get("detail", ""))}</td></tr>')
    matrix_html = ("\n".join(rows) if rows else
                   '<tr><td colspan="3" class="unknown">'
                   "no matrix checks recorded — NOT VERIFIED</td></tr>")
    missing_html = ("none" if not a["missing_evidence"] else
                    ", ".join(f"<code>{_esc(m)}</code>"
                              for m in a["missing_evidence"]))
    replay_html = ("PASS — chain replays clean"
                   if not a["chain_errors"] else
                   "FAIL — " + _esc("; ".join(a["chain_errors"]), 500))
    red_html = ("none" if not redacted else
                ", ".join(f"<code>{_esc(r, 120)}</code>" for r in redacted))
    why_html = "".join(f"<li>{_esc(w, 200)}</li>" for w in a["why"])

    body = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Dossier {_esc(op_id, 64)} — {_esc(verdict, 16)}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:60em;margin:2em auto;
padding:0 1em;color:#222}}table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #bbb;padding:.3em .6em;text-align:left;
font-size:.92em}}.pass{{color:#0a5;font-weight:bold}}
.fail{{color:#c00;font-weight:bold}}.unknown{{color:#a60;font-weight:bold}}
.badge{{display:inline-block;padding:.2em .8em;border-radius:.4em;
color:#fff}}.badge.pass{{background:#0a5}}.badge.fail{{background:#c00}}
.badge.unknown{{background:#a60}}code{{background:#f2f2f2}}
.note{{color:#555;font-size:.9em}}</style></head><body>
<h1>GENESIS RT engineering dossier</h1>
<p>op <code>{_esc(op_id, 64)}</code> ·
workflow <code>{_esc((rec.get("workflow") or "?"), 60)}</code> ·
<span class="badge {badge}">{_esc(verdict, 16)}</span></p>
<h2>Executive summary</h2>
<table><tr><th>Item</th><th>Value</th></tr>
<tr><td>Machine</td><td>{_esc(a["machine"], 120)}</td></tr>
<tr><td>Op state</td><td>{_esc(a["state"], 32)}</td></tr>
<tr><td>Gate verdict</td><td>{_esc(a["gate"], 16)}</td></tr>
<tr><td>Release eligible</td><td>{_esc(a["release_eligible"], 8)}</td></tr>
<tr><td>QNX verified</td><td>{_esc(a["qnx_verified"], 8)}</td></tr>
<tr><td>Matrix</td><td>{n_pass}/{len(checks)} checks passed</td></tr>
<tr><td>Perf samples</td><td>{_esc(a["perf_samples"], 8)}</td></tr>
<tr><td>IR digest</td><td><code>{_esc(a["ir_digest"], 80)}</code></td></tr>
<tr><td>Toolchain</td><td>{_esc(a["toolchain"], 160)}</td></tr>
<tr><td>Missing evidence</td><td>{missing_html}</td></tr>
<tr><td>Redacted keys</td><td>{red_html}</td></tr></table>
<h2>Why this verdict</h2>
<ul>{why_html}</ul>
<h2>Verification matrix (native QNX)</h2>
<table><tr><th>Check</th><th>Result</th><th>Detail</th></tr>
{matrix_html}</table>
<h2>Evidence replay</h2>
<p class="{"pass" if not a["chain_errors"] else "fail"}">{replay_html}</p>
<p class="note">Replayed with the repo verifier over the bundled
passport.json. Digests of every bundled file are in manifest.json.</p>
<h2>Change impact</h2>
<p>No baseline op is linked to this record, so no before/after diff is
shown. Compare IR digests across dossiers to attribute behavior changes
to specification changes.</p>
<h2>Limitations</h2>
<ul><li>Virtual machine outputs only; no physical actuation.</li>
<li>QNX runs under QEMU here, not on physical hardware; timings are
regression aids, not hard-real-time guarantees.</li>
<li>This dossier is engineering evidence, not a safety certification.</li>
<li>Hash-linked integrity, not hardware-backed attestation.</li></ul>
<p class="note">Generated {_esc(_utc_now())} by GENESIS RT dossier v{
        DOSSIER_VERSION}. Raw files ship alongside this report.</p>
</body></html>"""
    return body, verdict


_VERIFY_MD = """# Verify this dossier offline (no QNX SDK, no network)

1. Unzip the archive.
2. Check every file digest against manifest.json:

```sh
python -c "import hashlib,json,sys; m=json.load(open('manifest.json')); \\
sys.exit('OK' if all(hashlib.sha256(open(f,'rb').read()).hexdigest()==d \\
for f,d in m['files'].items()) else 'DIGEST MISMATCH')"
```

3. Open report.html in any browser.
4. Compare the verdict banner with the matrix table: a green PASS
   requires COMPLETED + gate PASS + QNX verified + clean replay.
   Anything else must show FAIL or NOT VERIFIED — if it shows green,
   the report itself is suspect.
"""


def build_dossier_zip(ops_dir: str | Path, op_id: str,
                      artifacts_root: str | Path | None = None) -> bytes:
    """Build the portable dossier ZIP for a terminal op.

    Raises DossierError with an HTTP-style status (404/409/413).
    """
    ops_path = Path(ops_dir)
    root = Path(artifacts_root) if artifacts_root else None
    files, rec, redacted = collect_op_files(ops_path, op_id, root)
    report, _verdict = render_report(op_id, rec, files, redacted)
    prefix = f"dossier-{op_id}/"
    files["report.html"] = _lf(report.encode("utf-8"))
    files["VERIFY.md"] = _lf(_VERIFY_MD.encode("utf-8"))
    manifest = {
        "dossier_version": DOSSIER_VERSION,
        "op_id": op_id,
        "created_utc": _utc_now(),
        "redacted_keys": redacted,
        "files": {name: hashlib.sha256(data).hexdigest()
                  for name, data in sorted(files.items())},
    }
    files["manifest.json"] = json.dumps(manifest, indent=1).encode("utf-8")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(files):
            zf.writestr(prefix + name, files[name])
    return buf.getvalue()

