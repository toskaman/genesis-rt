# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Titan W6: external build-manifest checks (BYOQNX minimal adapter).

The adapter detects stale artifacts in an existing project's build
directory. It must never evaluate imported test verdicts and never
grant release eligibility.
"""
import ast
import hashlib
import json
from pathlib import Path

import pytest

from genesis_rt.external import (EXTERNAL_MANIFEST_VERSION,
                                 ExternalManifestError, check_workspace,
                                 load_manifest, render_text)


def _manifest(**kw):
    base = {"external_manifest_version": EXTERNAL_MANIFEST_VERSION,
            "project": "demo-controller",
            "toolchain": "qcc 12.2.0 gcc_ntox86_64 (recorded, not verified)",
            "binaries": {},
            "test_claims": []}
    base.update(kw)
    return base


def _write_workspace(tmp_path, files):
    ws = tmp_path / "ws"
    ws.mkdir()
    manifest_bins = {}
    for name, blob in files.items():
        target = ws / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
        manifest_bins[name] = {"sha256": hashlib.sha256(blob).hexdigest(),
                               "size": len(blob)}
    man = _manifest(binaries=manifest_bins)
    man_path = tmp_path / "manifest.json"
    man_path.write_text(json.dumps(man), encoding="utf-8")
    return man_path, ws


def test_consistent_workspace_matches(tmp_path):
    man_path, ws = _write_workspace(tmp_path, {"guard": b"elf-bytes-1",
                                               "ctrl": b"elf-bytes-2"})
    report = check_workspace(man_path, ws)
    assert report["verdict"] == "CONSISTENT"
    assert report["release_eligible"] is False
    assert all(b["status"] == "MATCH"
               for b in report["binaries"].values())


def test_tampered_binary_is_stale(tmp_path):
    man_path, ws = _write_workspace(tmp_path, {"guard": b"elf-bytes-1"})
    (ws / "guard").write_bytes(b"elf-bytes-TAMPERED")
    report = check_workspace(man_path, ws)
    assert report["verdict"] == "STALE"
    assert report["stale_binaries"] == ["guard"]
    assert report["binaries"]["guard"]["status"] == "MISMATCH"
    assert report["release_eligible"] is False


def test_missing_binary_is_absent_not_match(tmp_path):
    man_path, ws = _write_workspace(tmp_path, {"guard": b"elf-bytes-1"})
    (ws / "guard").unlink()
    report = check_workspace(man_path, ws)
    assert report["verdict"] == "STALE"
    assert report["binaries"]["guard"]["status"] == "ABSENT"


def test_size_change_is_mismatch_even_with_same_prefix(tmp_path):
    man_path, ws = _write_workspace(tmp_path, {"guard": b"abcd"})
    (ws / "guard").write_bytes(b"abcde")
    report = check_workspace(man_path, ws)
    assert report["binaries"]["guard"]["status"] == "MISMATCH"


def test_traversal_names_refused_before_any_read(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    secret = tmp_path / "secret.bin"
    secret.write_bytes(b"top-secret")
    for evil in ("../secret.bin", "..\\secret.bin", "/abs/path",
                 "C:/Windows/win.ini", "sub/../../secret.bin"):
        man = _manifest(binaries={evil: {
            "sha256": hashlib.sha256(b"top-secret").hexdigest()}})
        with pytest.raises(ExternalManifestError, match="escapes the workspace"):
            check_workspace(man, ws)


def test_nested_inside_workspace_allowed(tmp_path):
    man_path, ws = _write_workspace(tmp_path, {"bin/sub/guard": b"nested"})
    report = check_workspace(man_path, ws)
    assert report["verdict"] == "CONSISTENT"


def test_schema_is_fail_closed(tmp_path):
    good = _manifest(binaries={"g": {"sha256": "ab" * 32}})
    bad_cases = [
        {**good, "external_manifest_version": 2},
        {**good, "project": ""},
        {**good, "binaries": {}},
        {**good, "binaries": {"g": {"sha256": "xyz"}}},
        {**good, "binaries": {"g": {"sha256": "ab" * 32, "size": -1}}},
        {**good, "binaries": {"g": {"sha256": "ab" * 32, "extra": 1}}},
        {**good, "future_key": 1},
        {**good, "test_claims": [{"name": "t", "verdict": "maybe"}]},
        {**good, "test_claims": [{"name": "", "verdict": "pass"}]},
        "not-a-dict",
    ]
    for bad in bad_cases:
        with pytest.raises(ExternalManifestError):
            load_manifest(_dump(tmp_path, bad))


def _dump(tmp_path, obj):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(obj), encoding="utf-8")
    return p


def test_uppercase_hex_accepted_and_lowered(tmp_path):
    man = _manifest(binaries={"g": {"sha256": "AB" * 32}})
    assert load_manifest(_dump(tmp_path, man))["binaries"]["g"]["sha256"] == "ab" * 32


def test_claims_counted_never_evaluated(tmp_path):
    man_path, ws = _write_workspace(tmp_path, {"guard": b"elf"})
    man = json.loads(man_path.read_text(encoding="utf-8"))
    man["test_claims"] = [{"name": "smoke", "verdict": "pass"},
                          {"name": "fault", "verdict": "fail",
                           "detail": "jam did not latch"}]
    man_path.write_text(json.dumps(man), encoding="utf-8")
    report = check_workspace(man_path, ws)
    assert report["test_claims"]["trust"] == "UNVERIFIED_CLAIM"
    assert (report["test_claims"]["claimed_pass"],
            report["test_claims"]["claimed_fail"]) == (1, 1)
    # A failing claimed test does not change the digest verdict, and a
    # passing one never grants eligibility.
    assert report["verdict"] == "CONSISTENT"
    assert report["release_eligible"] is False


def test_render_text_names_stale_and_scope(tmp_path):
    man_path, ws = _write_workspace(tmp_path, {"guard": b"elf"})
    (ws / "guard").write_bytes(b"changed")
    text = render_text(check_workspace(man_path, ws))
    assert "MISMATCH guard" in text
    assert "release_eligible: False" in text
    assert "digest consistency only" in text


def test_cli_exit_codes(tmp_path, capsys):
    from genesis_rt.cli import main
    man_path, ws = _write_workspace(tmp_path, {"guard": b"elf"})
    assert main(["external-check", str(man_path),
                 "--workspace", str(ws)]) == 0
    (ws / "guard").write_bytes(b"changed")
    assert main(["external-check", str(man_path),
                 "--workspace", str(ws)]) == 2
    assert main(["external-check", str(man_path), "--workspace",
                 str(ws), "--json"]) == 2
    out = capsys.readouterr().out
    assert '"verdict": "STALE"' in out
    assert main(["external-check", str(tmp_path / "nope.json"),
                 "--workspace", str(ws)]) == 2


def test_adapter_has_no_gate_or_target_imports():
    """The trust boundary is structural: external.py must not reach the
    release gate, the evidence chain, or the target runner."""
    src = (Path(__file__).resolve().parents[2] / "host" / "genesis_rt" /
           "external.py").read_text(encoding="utf-8")
    mods = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.update([node.module.split(".")[0]] +
                        [a.name.split(".")[0] for a in node.names])
    assert not ({"gate", "evidence", "target", "orchestrator",
                 "provenance", "runner"} & mods), mods


def test_missing_workspace_refused(tmp_path):
    man_path, _ws = _write_workspace(tmp_path, {"guard": b"elf"})
    with pytest.raises(ExternalManifestError, match="not a directory"):
        check_workspace(man_path, tmp_path / "nope")


def test_write_manifest_roundtrip(tmp_path):
    from genesis_rt.external import write_manifest
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "guard").write_bytes(b"elf-1")
    (ws / "ctrl").write_bytes(b"elf-2")
    man = write_manifest(ws, "demo", "qcc 12.2.0 (recorded, not verified)")
    assert sorted(man["binaries"]) == ["ctrl", "guard"]
    report = check_workspace(man, ws)
    assert report["verdict"] == "CONSISTENT"
    (ws / "guard").write_bytes(b"elf-1+patch")
    assert check_workspace(man, ws)["stale_binaries"] == ["guard"]


def test_write_manifest_only_and_empty(tmp_path):
    from genesis_rt.external import write_manifest
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "guard").write_bytes(b"elf-1")
    man = write_manifest(ws, "demo", "tool", names=["guard"])
    assert sorted(man["binaries"]) == ["guard"]
    with pytest.raises(ExternalManifestError, match="not found"):
        write_manifest(ws, "demo", "tool", names=["missing"])
    with pytest.raises(ExternalManifestError, match="escapes"):
        write_manifest(ws, "demo", "tool", names=["../x"])
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ExternalManifestError, match="no files"):
        write_manifest(empty, "demo", "tool")
