# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Wave 11 §5: limits_differ contract-aware parsing (no target).

Flagship BEFORE/AFTER transcripts are hand-written literals (not
oracle-generated: the parser test must not share the oracle under
test). Other limits use oracle-built transcripts to exercise parser
plumbing; verdict-correctness itself is pinned by the oracle hand
vectors + C conformance. The real Wave 10 BEFORE log pins the legacy
unattested path.
"""
import importlib.util

import pytest

from genesis_rt import native_oracle as no

PACK = "evidence/qnx8-x86_64-verified-b22cea1/transcripts"


def _load_qt(repo_root):
    spec = importlib.util.spec_from_file_location(
        "qnx_target_under_test", repo_root / "scripts" / "qnx_target.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def qt(repo_root):
    return _load_qt(repo_root)


def _bound(limit, kind="differential_drive_robot",
           mid="amr-demo-01"):
    return {"machine_id": mid, "machine_kind": kind,
            "ir_sha256": "ab" * 32, "linear_limit_mps": limit}


def _probe_line(echo, decision, reason, state=1):
    return (f"PROBE linear={echo} estop=0 decision={decision} "
            f"reason={reason} state={state}")


def _wrap(slot1_lines, conv_lines, mid, lim):
    return "\n".join(
        ["---PROBE-AMR---", *slot1_lines, "---PROBE-CONV---",
         *conv_lines, "---FI-VS-CONV---", "ALL 9 CHECKS PASS",
         "FI_CONV_EXIT=0", "---GUARD-HEADERS---",
         f"machine={mid} limits linear={lim:.3f}",
         "machine=conveyor-demo-01 limits linear=2.000", ""])


def _oracle_transcript(limit, mid="amr-demo-01",
                       kind="differential_drive_robot"):
    """Plumbing transcripts (verdicts via the pinned oracle)."""
    plan = no.plan_probes(limit)
    assert plan is not None
    s1, cv = [], []
    for value in plan:
        echo = "%.3f" % value
        for slot, lim, out in ((kind, limit, s1),
                               ("conveyor", 2.0, cv)):
            want = no.expect_linear_probe(machine_kind=slot,
                                          limit_mps=lim, probe_mps=value)
            out.append(_probe_line(echo, want.decision, want.reason,
                                   want.state_out))
    return _wrap(s1, cv, mid, limit)


# Hand-derived BEFORE (1.2): slot1 ALLOW, DENY(f32!), DENY, DENY.
BEFORE_12 = _wrap(
    [_probe_line("0.600", "ALLOW", "OK"),
     _probe_line("1.200", "DENY", "SPEED_OVER_LIMIT"),
     _probe_line("1.500", "DENY", "SPEED_OVER_LIMIT"),
     _probe_line("1.700", "DENY", "SPEED_OVER_LIMIT")],
    [_probe_line("0.600", "ALLOW", "OK"),
     _probe_line("1.200", "ALLOW", "OK"),
     _probe_line("1.500", "ALLOW", "OK"),
     _probe_line("1.700", "ALLOW", "OK")],
    "amr-demo-01", 1.2)

# Hand-derived AFTER (1.6): 1.5 flips to ALLOW, boundaries still deny.
AFTER_16 = _wrap(
    [_probe_line("0.800", "ALLOW", "OK"),
     _probe_line("1.500", "ALLOW", "OK"),
     _probe_line("1.600", "DENY", "SPEED_OVER_LIMIT"),
     _probe_line("2.100", "DENY", "SPEED_OVER_LIMIT")],
    [_probe_line("0.800", "ALLOW", "OK"),
     _probe_line("1.500", "ALLOW", "OK"),
     _probe_line("1.600", "ALLOW", "OK"),
     _probe_line("2.100", "DENY", "SPEED_OVER_LIMIT")],
    "amr-demo-01", 1.6)


def test_before_literal_passes(qt):
    assert qt._matrix_check("limits_differ", BEFORE_12, 0,
                            _bound(1.2))["passed"] is True


def test_after_literal_passes(qt):
    assert qt._matrix_check("limits_differ", AFTER_16, 0,
                            _bound(1.6))["passed"] is True


@pytest.mark.parametrize("limit", [0.3, 0.5, 2.0])
def test_other_limits_pass(qt, limit):
    assert qt._matrix_check("limits_differ",
                            _oracle_transcript(limit), 0,
                            _bound(limit))["passed"] is True


def _mutate(body, old, new, count=1):
    assert old in body
    return body.replace(old, new, count)


def test_flipped_slot1_verdict_fails(qt):
    bad = _mutate(AFTER_16,
                  "PROBE linear=1.500 estop=0 decision=ALLOW reason=OK",
                  "PROBE linear=1.500 estop=0 decision=DENY "
                  "reason=SPEED_OVER_LIMIT")
    assert qt._matrix_check("limits_differ", bad, 0,
                            _bound(1.6))["passed"] is False


def test_flipped_conv_verdict_fails(qt):
    bad = _mutate(BEFORE_12,
                  "PROBE linear=1.500 estop=0 decision=ALLOW reason=OK",
                  "PROBE linear=1.500 estop=0 decision=DENY "
                  "reason=SPEED_OVER_LIMIT")
    assert qt._matrix_check("limits_differ", bad, 0,
                            _bound(1.2))["passed"] is False


def test_missing_probe_line_fails(qt):
    bad = _mutate(AFTER_16, _probe_line("1.600", "DENY",
                                        "SPEED_OVER_LIMIT") + "\n", "")
    assert qt._matrix_check("limits_differ", bad, 0,
                            _bound(1.6))["passed"] is False


def test_wrong_banner_fails(qt):
    bad = _mutate(AFTER_16, "machine=amr-demo-01 limits linear=1.600",
                  "machine=amr-demo-01 limits linear=1.200")
    assert qt._matrix_check("limits_differ", bad, 0,
                            _bound(1.6))["passed"] is False


def test_missing_fi_fails(qt):
    bad = _mutate(AFTER_16, "FI_CONV_EXIT=0", "FI_CONV_EXIT=1")
    assert qt._matrix_check("limits_differ", bad, 0,
                            _bound(1.6))["passed"] is False


def test_unknown_kind_fails_closed(qt):
    assert qt._matrix_check(
        "limits_differ", AFTER_16, 0,
        _bound(1.6, kind="robot_arm"))["passed"] is False


def test_conv_as_slot1_fails(qt):
    assert qt._matrix_check(
        "limits_differ", AFTER_16, 0,
        _bound(2.0, kind="conveyor",
               mid="conveyor-demo-01"))["passed"] is False


def test_no_plan_marker_fails(qt):
    body = "ORACLE_NO_PLAN_FOR_LIMIT\n"
    assert qt._matrix_check("limits_differ", body, 3,
                            _bound(0.001))["passed"] is False


def _pack_stdout(repo_root):
    """Stdout section of the archived log (strip the `$ command` and
    `[exit=..]` framing the runner adds around real stdout)."""
    lines = (repo_root / PACK / "target-limits_differ.log").read_text(
        encoding="utf-8").splitlines()
    assert lines[0].startswith("$ ") and lines[-1].startswith("[exit=")
    return "\n".join(lines[1:-1]) + "\n"


def test_legacy_pack_log_still_passes_unattested(qt, repo_root):
    body = _pack_stdout(repo_root)
    assert qt._matrix_check("limits_differ", body, 0,
                            None)["passed"] is True


def test_legacy_path_blind_to_after(qt, repo_root):
    """Documents the pre-Wave-11 blindness: the unattested legacy
    assertions reject a correct 1.6 guard (ALLOW@1.5)."""
    body = _pack_stdout(repo_root)
    bad = _mutate(body,
                  "decision=DENY reason=SPEED_OVER_LIMIT",
                  "decision=ALLOW reason=OK")
    assert qt._matrix_check("limits_differ", bad, 0, None)["passed"] is False


def test_command_builder_bound_and_legacy(qt):
    dyn = qt._limits_differ_command(_bound(1.6))
    assert "probe 0.800" in dyn and "probe 2.100" in dyn
    assert "---PROBE-AMR---" in dyn and "---PROBE-CONV---" in dyn
    assert dyn.count("sleep 2") >= 8  # guard restarts per probe
    legacy = next(c for n, c in qt.TARGET_MATRIX if n == "limits_differ")
    assert qt._limits_differ_command(None) == legacy
    assert "ORACLE_NO_PLAN_FOR_LIMIT" in \
        qt._limits_differ_command(_bound(0.001))
