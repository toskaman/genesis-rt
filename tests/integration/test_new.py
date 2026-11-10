# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Integration tests: W4 new (guided first-machine builder)."""
import json

from genesis_rt.cli import main
from genesis_rt.newmachine import OFFERED_KINDS, build_machine_ir


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_build_conveyor_sets_id_and_validates(tmp_path):
    out = tmp_path / "conv.json"
    ir = build_machine_ir("conveyor", "conv-1", {}, out)
    assert ir["machine"]["id"] == "conv-1"
    assert ir["machine"]["kind"] == "conveyor"
    assert _read(out)["machine"]["id"] == "conv-1"
    assert main(["validate", str(out)]) == 0


def test_build_knob_override_coerces_and_validates(tmp_path):
    out = tmp_path / "conv.json"
    ir = build_machine_ir("conveyor", "c2", {"max_linear_speed_mps": "2.0"},
                          out)
    assert ir["control"]["max_linear_speed_mps"] == 2.0
    assert main(["validate", str(out)]) == 0


def test_build_unknown_knob_rejected(tmp_path):
    import pytest
    from genesis_rt.newmachine import NewMachineError
    with pytest.raises(NewMachineError):
        build_machine_ir("conveyor", "c3", {"nope": "1"}, tmp_path / "x.json")


def test_build_bad_value_rejected(tmp_path):
    import pytest
    from genesis_rt.newmachine import NewMachineError
    with pytest.raises(NewMachineError):
        build_machine_ir("conveyor", "c4",
                         {"max_linear_speed_mps": "fast"},
                         tmp_path / "x.json")


def test_build_arm_not_offered(tmp_path):
    import pytest
    from genesis_rt.newmachine import NewMachineError
    assert "robotic_arm_virtual" not in OFFERED_KINDS
    with pytest.raises(NewMachineError, match="arm physics"):
        build_machine_ir("robotic_arm_virtual", "a1", {},
                         tmp_path / "x.json")


def test_cli_new_writes_and_validates(tmp_path, capsys):
    out = tmp_path / "cell.json"
    rc = main(["new", "--kind", "industrial_cell", "--id", "cell-9",
               "--out", str(out)])
    assert rc == 0
    assert _read(out)["machine"]["id"] == "cell-9"
    assert "next:" in capsys.readouterr().out


def test_cli_new_short_alias(tmp_path):
    out = tmp_path / "a.json"
    assert main(["new", "--kind", "amr", "--id", "amr-2",
                 "--out", str(out)]) == 0
    assert _read(out)["machine"]["kind"] == "differential_drive_robot"


def test_cli_new_set_flag(tmp_path):
    out = tmp_path / "c.json"
    rc = main(["new", "--kind", "conveyor", "--id", "c5",
               "--out", str(out), "--set", "max_linear_speed_mps=2.5"])
    assert rc == 0
    assert _read(out)["control"]["max_linear_speed_mps"] == 2.5


def test_cli_new_refuses_overwrite(tmp_path, capsys):
    out = tmp_path / "c.json"
    out.write_text("{}", encoding="utf-8")
    rc = main(["new", "--kind", "cell", "--id", "c6", "--out", str(out)])
    assert rc == 2
    assert "--force" in capsys.readouterr().out
    rc = main(["new", "--kind", "cell", "--id", "c6", "--out", str(out),
               "--force"])
    assert rc == 0


def test_cli_new_interactive(monkeypatch, tmp_path, capsys):
    out = tmp_path / "i.json"
    answers = iter(["conveyor", "conv-i", "", "", "", ""])  # 4 knobs keep
    monkeypatch.setattr("builtins.input", lambda *a: next(answers))
    rc = main(["new", "--interactive", "--out", str(out)])
    assert rc == 0, capsys.readouterr().out
    ir = _read(out)
    assert ir["machine"]["id"] == "conv-i"
    assert ir["machine"]["kind"] == "conveyor"
    assert main(["validate", str(out)]) == 0


def test_cli_new_interactive_arm_rejected(monkeypatch, tmp_path, capsys):
    out = tmp_path / "i.json"
    answers = iter(["robotic_arm_virtual"])
    monkeypatch.setattr("builtins.input", lambda *a: next(answers))
    rc = main(["new", "--interactive", "--out", str(out)])
    assert rc == 2
    assert "arm physics" in capsys.readouterr().out
