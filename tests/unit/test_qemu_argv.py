# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: QEMU argv construction (accel/cpu defaults that boot QNX)."""
import importlib.util

import pytest


def _load_qnx_target(repo_root):
    spec = importlib.util.spec_from_file_location(
        "qnx_target_argv", repo_root / "scripts" / "qnx_target.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def qt(repo_root):
    return _load_qnx_target(repo_root)


@pytest.fixture()
def image_dir(tmp_path):
    out = tmp_path / "img" / "output"
    out.mkdir(parents=True)
    (out / "ifs.bin").write_bytes(b"ifs")
    (out / "disk-qemu.vmdk").write_bytes(b"disk")
    return tmp_path / "img"


def _cpu_of(argv):
    assert "-cpu" in argv
    return argv[argv.index("-cpu") + 1]


def test_tcg_defaults_to_cpu_max(qt, image_dir):
    """QNX spins on default qemu64 under TCG (proven stuck guest); max boots."""
    argv = qt.build_qemu_argv("qemu", image_dir, accel="tcg", boot="disk")
    assert _cpu_of(argv) == "max"
    assert "-accel" not in argv  # tcg is QEMU's default backend


def test_tcg_rejects_host_cpu(qt, image_dir):
    with pytest.raises(ValueError, match="hardware accelerator"):
        qt.build_qemu_argv("qemu", image_dir, accel="tcg", boot="disk",
                           cpu="host")


def test_tcg_honors_explicit_cpu(qt, image_dir):
    argv = qt.build_qemu_argv("qemu", image_dir, accel="tcg", boot="disk",
                             cpu="Haswell")
    assert _cpu_of(argv) == "Haswell"


def test_whpx_keeps_host_passthrough(qt, image_dir, monkeypatch):
    monkeypatch.setenv("PROCESSOR_IDENTIFIER", "Intel64 Family 6")
    argv = qt.build_qemu_argv("qemu", image_dir, accel="whpx", boot="disk")
    assert _cpu_of(argv) == "host"
    assert argv[argv.index("-accel") + 1] == "whpx"


def test_device_chain_status_runs_as_root(qt):
    """resmgr_attach() needs root: the device_chain status leg must start
    and be cleaned up via sudo, or the node never appears (EPERM)."""
    body = dict(qt.TARGET_MATRIX)["device_chain"]
    assert "sudo -n ./genesis_status /tmp/genesis-status-node" in body
    assert body.count("sudo -n slay genesis_status") >= 2  # setup + cleanup


def test_conv_chain_step_shape(qt):
    """conv_chain mirrors device_chain idioms: belt device, conv guard
    with missing-guard tripwire, sudo status, pid audit, cleanup."""
    body = dict(qt.TARGET_MATRIX)["conv_chain"]
    assert "./genesis_device belt" in body
    assert "./genesis_guard_conv" in body
    assert "MISSING_CONV_GUARD" in body
    assert "sudo -n ./genesis_status /tmp/genesis-status-node" in body
    assert body.count("sudo -n slay genesis_status") >= 2
    assert "from_pid=$GUARDPID" in body
    assert "belt_pos" in body
    assert "slay genesis_guard_conv" in body


def _conv_chain_body(**over):
    parts = {"STATUS_EXIT=0": True, "belt mode": True,
             "dev_applied=25": True, "dev_x=1.234": True,
             "dev_v=0.500": True, "fwd_ok=25": True, "fwd_fail=0": True,
             "APPLIES=25": True, "BELT=25": True, "NONGUARD=0": True}
    parts.update(over)
    return "\n".join(k for k, v in parts.items() if v)


def test_conv_chain_parser_accepts_and_rejects(qt):
    assert qt._matrix_check("conv_chain", _conv_chain_body(), 0)["passed"] is True
    assert qt._matrix_check(
        "conv_chain", _conv_chain_body(**{"BELT=25": False, "BELT=3": True}),
        0)["passed"] is False  # pose lines instead of belt
    assert qt._matrix_check(
        "conv_chain", _conv_chain_body(**{"dev_x=1.234": False, "dev_x=0.1": True}),
        0)["passed"] is False  # belt never moved
    assert qt._matrix_check(
        "conv_chain", _conv_chain_body(**{"NONGUARD=0": False, "NONGUARD=2": True}),
        0)["passed"] is False  # bypass
    assert qt._matrix_check(
        "conv_chain", _conv_chain_body() + "\nMISSING_CONV_GUARD", 0,
    )["passed"] is False


def _bench_body(n, done=None, bad_line=False):
    lines = [f"SAMPLE {10.0 + i * 0.001:.3f}" for i in range(n)]
    if bad_line:
        lines[n // 2] = "SAMPLE oops"
    lines.append(f"PERF_DONE n={n if done is None else done}")
    return "\n".join(lines) + "\n"


def test_target_perf_parser_accepts_and_rejects(qt):
    assert qt._matrix_check("target_perf", _bench_body(200), 0)["passed"] is True
    assert qt._matrix_check(
        "target_perf", _bench_body(199), 0)["passed"] is False  # short
    assert qt._matrix_check(
        "target_perf", _bench_body(200, done=199), 0)["passed"] is False
    assert qt._matrix_check(
        "target_perf", _bench_body(200, bad_line=True), 0)["passed"] is False


def test_perf_distribution_nearest_rank(qt):
    d = qt._perf_distribution([float(i) for i in range(1, 101)])
    assert d == {"count": 100, "unit": "microseconds", "min": 1.0,
                 "max": 100.0, "p50": 50.0, "p95": 95.0, "p99": 99.0}
    d = qt._perf_distribution([5.0])
    assert (d["count"], d["p50"], d["p99"]) == (1, 5.0, 5.0)


def _drive_spec(argv):
    assert "-drive" in argv
    return argv[argv.index("-drive") + 1]


def _image_dir_with(tmp_path, disk_name):
    out = tmp_path / "imgfmt" / "output"
    out.mkdir(parents=True)
    (out / "ifs.bin").write_bytes(b"ifs")
    (out / disk_name).write_bytes(b"disk")
    return tmp_path / "imgfmt"


def test_vmdk_pins_explicit_format(qt, image_dir):
    """A .vmdk disk must not rely on QEMU probing: a damaged descriptor
    probes as raw and the guest silently loses its disk (2026-11-05)."""
    argv = qt.build_qemu_argv("qemu", image_dir, accel="tcg", boot="disk")
    assert "format=vmdk" in _drive_spec(argv)


def test_qcow2_pins_explicit_format(qt, tmp_path):
    img = _image_dir_with(tmp_path, "disk.qcow2")
    argv = qt.build_qemu_argv("qemu", img, accel="tcg", boot="disk")
    assert "format=qcow2" in _drive_spec(argv)


def test_suffixless_disk_pins_raw(qt, tmp_path):
    img = _image_dir_with(tmp_path, "disk-qemu")
    argv = qt.build_qemu_argv("qemu", img, accel="tcg", boot="disk",
                             disk_name="disk-qemu")
    assert "format=raw" in _drive_spec(argv)


def test_estop_target_parser_accepts_and_rejects(qt):
    good = ("guard: reset handler installed (SIGUSR1)\n"
            "---ESTOP-PROBE---\n"
            "PROBE linear=0.500 estop=1 decision=DENY reason=ESTOP state=3\n"
            "---STATUS-ESTOP---\n"
            "state=3 last_reason=ESTOP allows=0 denies=1\n"
            "STATUS_EXIT=0\n"
            "---OPERATOR-RESET---\n"
            "guard: operator reset armed (SIGUSR1)\n"
            "---RESET-PROBE---\n"
            "PROBE state=0 decision=DENY reason=BAD_TRANSITION state=3\n"
            "PROBE linear=0.400 estop=0 decision=ALLOW reason=OK state=1\n")
    assert qt._matrix_check("estop_target", good, 0)["passed"] is True
    assert qt._matrix_check("estop_target", good.replace(
        "reason=ESTOP", "reason=OK"), 0)["passed"] is False
    assert qt._matrix_check("estop_target", good.replace(
        "state=3 ", "state=1 "), 0)["passed"] is False  # latch missing
    assert qt._matrix_check("estop_target", good.replace(
        "STATUS_EXIT=0", "STATUS_EXIT=1"), 0)["passed"] is False
    no_reset = good.split("---OPERATOR-RESET---")[0]
    assert qt._matrix_check("estop_target", no_reset, 0)["passed"] is False
    stuck = good.replace("PROBE linear=0.400 estop=0 decision=ALLOW "
                         "reason=OK state=1",
                         "PROBE linear=0.400 estop=0 decision=DENY "
                         "reason=BAD_TRANSITION state=3")
    assert qt._matrix_check("estop_target", stuck, 0)["passed"] is False


def test_reset_armed_wire_has_single_source_site(qt, repo_root):
    """The parser greps ONE consumption message; startup must not collide.

    Native 8-Nov finding: the install-OK banner also contained
    "operator reset armed", so the grep matched before any signal was
    consumed. Exactly one site may print it, in (SIGUSR1) form.
    """
    src = (repo_root / "target" / "qnx8" / "guard"
           / "genesis_guard.c").read_text(encoding="utf-8")
    hits = [line for line in src.splitlines()
            if "operator reset armed" in line]
    assert len(hits) == 1
    assert "(SIGUSR1)" in hits[0]


_V2_BOUND = {"machine_id": "amr-demo-01", "schema_version": 2,
              "ir_sha256": "x" * 64, "linear_limit_mps": 0.8}
_V1_BOUND = {"machine_id": "amr-demo-01", "schema_version": 1,
             "ir_sha256": "y" * 64, "linear_limit_mps": 1.2}


def _v2_estop_body():
    return ("guard: reset handler installed (SIGUSR1)\n"
            "---ESTOP-PROBE---\n"
            "PROBE linear=0.500 estop=1 decision=DENY reason=ESTOP state=3\n"
            "---STATUS-ESTOP---\n"
            "state=3 last_reason=ESTOP allows=0 denies=1\n"
            "STATUS_EXIT=0\n"
            "---OPERATOR-RESET---\n"
            "---RESET-PROBE---\n"
            "PROBE state=0 decision=ALLOW reason=OK state=0\n"
            "PROBE linear=0.400 estop=0 decision=ALLOW reason=OK state=1\n"
            "guard: operator reset armed (SIGUSR1)\n")


def test_estop_v2_requires_declared_reset_transition(qt):
    """v2 has no safe_stop->running edge: reset must go through the
    declared safe_stop->init transition (state=0 ALLOW) first."""
    good = _v2_estop_body()
    assert qt._matrix_check("estop_target", good, 0,
                            _V2_BOUND)["passed"] is True
    # A guard that jumps straight to running skips the contract.
    skipped = good.replace(
        "PROBE state=0 decision=ALLOW reason=OK state=0\n", "")
    assert qt._matrix_check("estop_target", skipped, 0,
                            _V2_BOUND)["passed"] is False
    # v1 has no transition table: the same tail still passes there.
    assert qt._matrix_check("estop_target", skipped, 0,
                            _V1_BOUND)["passed"] is True
    assert qt._matrix_check("estop_target", skipped, 0,
                            None)["passed"] is True
    stuck = good.replace("state=0 decision=ALLOW",
                         "state=0 decision=DENY")
    assert qt._matrix_check("estop_target", stuck, 0,
                            _V2_BOUND)["passed"] is False


def _v2trans_body(marker):
    return (marker + "\n"
            "---V1-STATE2---\nPROBE state=2 decision=ALLOW\n"
            "---V1-STATE3---\n"
            "PROBE state=3 decision=DENY reason=BAD_TRANSITION\n"
            "---V2-STATE2---\n"
            "PROBE state=2 decision=DENY reason=BAD_TRANSITION\n"
            "---V2-STATE3---\nPROBE state=3 decision=ALLOW\n"
            "---V2-SUITE---\nALL 9 CHECKS PASS\n" + "PASS x\n" * 9 +
            "FI_V2_EXIT=0\n"
            "---V2-LIMIT---\ndecision=DENY reason=SPEED_OVER_LIMIT\n"
            "---V2-ESTOP---\ndecision=DENY reason=ESTOP\n")


def test_v2transitions_bin_marker_follows_binding(qt):
    """v1 ops stage v1+v2 guards (DIFF_BIN); v2 ops stage v2 twice
    (slot-1 is v2) plus the v1 guard aside, so SAME_BIN is correct."""
    assert qt._matrix_check("v2_transitions", _v2trans_body("DIFF_BIN"),
                            0, None)["passed"] is True
    assert qt._matrix_check("v2_transitions", _v2trans_body("SAME_BIN"),
                            0, None)["passed"] is False
    assert qt._matrix_check("v2_transitions", _v2trans_body("DIFF_BIN"),
                            0, _V1_BOUND)["passed"] is True
    assert qt._matrix_check("v2_transitions", _v2trans_body("SAME_BIN"),
                            0, _V2_BOUND)["passed"] is True
    assert qt._matrix_check("v2_transitions", _v2trans_body("DIFF_BIN"),
                            0, _V2_BOUND)["passed"] is False


def test_estop_reset_uses_sequenced_state_probe(qt):
    """run_state_probe hardcodes seq=1: reusing it on the live (latched)
    guard yields STALE_SEQ, so the matrix must pass an explicit seq and
    order the state probe before the motion probe."""
    cmd = dict(qt.TARGET_MATRIX)["estop_target"]
    assert "probe state 0 2" in cmd
    assert cmd.index("probe state 0 2") < cmd.index("probe 0.4 3")


def test_v2transitions_runs_v1_sections_on_v1_binary(qt):
    """In v2 ops slot-1 is v2, so the V1 sections must prefer a staged
    v1 guard when present (else they would probe v2 twice)."""
    cmd = dict(qt.TARGET_MATRIX)["v2_transitions"]
    assert "genesis_guard_v1" in cmd
    assert cmd.index("V1BIN") < cmd.index("---V1-STATE2---")


def test_state_probe_usage_documents_optional_seq(repo_root):
    src = (repo_root / "target" / "qnx8" / "faultinject"
           / "genesis_faultinject.c").read_text(encoding="utf-8")
    assert "probe state <0..3> [seq]" in src


def test_verify_exit_code_fails_on_fatal_provenance(qt):
    """H9: a green matrix with broken provenance (unknown identity,
    unreadable staging, unloadable build-set) must not exit 0. Absent
    --ir/--build-set only cap the tier (soft, honestly reported)."""
    assert qt._verify_exit_code(True, []) == 0
    assert qt._verify_exit_code(False, []) == 1
    assert qt._verify_exit_code(True, ["staged inventory failed"]) == 1
    assert qt._verify_exit_code(True, ["target identity unknown"]) == 1


def test_estop_command_greps_reset_after_reset_probe(qt):
    """The arming print fires on the NEXT received message, so the log
    grep must run after (not before) the RESET-PROBE that consumes it."""
    cmd = dict(qt.TARGET_MATRIX)["estop_target"]
    assert cmd.index("grep 'operator reset armed'") > cmd.index(
        "---RESET-PROBE---")


def test_respawn_parser_requires_rebind_and_resumed_chain(qt):
    good = ("4\n"
            "1\n"
            "PRE_APPLIES=61\n"
            "REBIND_COUNT=1\n"
            "POST_APPLIES=83\n"
            "SETTLED=4\n")
    assert qt._matrix_check("supervisor_respawn", good, 0)["passed"] is True
    assert qt._matrix_check("supervisor_respawn", good.replace(
        "REBIND_COUNT=1", "REBIND_COUNT=0"), 0)["passed"] is False
    assert qt._matrix_check("supervisor_respawn", good.replace(
        "POST_APPLIES=83", "POST_APPLIES=61"), 0)["passed"] is False
    assert qt._matrix_check("supervisor_respawn", good.replace(
        "SETTLED=4", "SETTLED=3"), 0)["passed"] is False
    assert qt._matrix_check("supervisor_respawn", "3\n1\n", 0)["passed"] \
        is False
