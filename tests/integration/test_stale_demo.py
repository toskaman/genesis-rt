# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: scripted 30s stale-refusal demo (B2 rehearsal).

The demo script itself is the rehearsal artifact: these tests run it
end to end (seal -> CONSISTENT -> mutate -> STALE) and hold the
30-second budget, so every CI run re-rehearses the WOW beat.
"""
import subprocess
import sys
import time


def _demo(repo_root, *args):
    return subprocess.run(
        [sys.executable, "scripts/demo_stale_refusal.py", *args],
        capture_output=True, text=True, timeout=120, cwd=str(repo_root))


def test_stale_demo_refuses_live_then_points_at_archived(repo_root):
    t0 = time.monotonic()
    proc = _demo(repo_root)
    elapsed = time.monotonic() - t0
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "beat 1/3" in proc.stdout and "CONSISTENT" in proc.stdout
    assert "beat 2/3" in proc.stdout and "verdict: STALE" in proc.stdout
    assert "genesis_guard" in proc.stdout
    assert "beat 3/3" in proc.stdout and "archived, not live" in proc.stdout
    assert "the wrong binary cannot pass" in proc.stdout
    assert elapsed < 30, elapsed


def test_stale_demo_workspace_kept_on_request(repo_root, tmp_path):
    ws = tmp_path / "kept"
    proc = _demo(repo_root, "--workspace", str(ws))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (ws / "external-manifest.json").is_file()
    assert (ws / "genesis_guard").is_file()
