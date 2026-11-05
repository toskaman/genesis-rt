# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: project store revisions + structural IR diff (no HTTP)."""
import json

import pytest

from genesis_rt.ir import IRValidationError
from genesis_rt.projects import (ProjectFull, ProjectNotFound, ProjectStore,
                                 ir_diff, summarize, valid_name,
                                 valid_project_id, validate_any)


@pytest.fixture()
def store(tmp_path):
    return ProjectStore(tmp_path / "projects")


def test_validate_any_dispatches_versions(amr_ir_dict, repo_root):
    v, valid = validate_any(amr_ir_dict)
    assert v == 1 and valid["machine"]["id"] == "amr-demo-01"
    v2 = json.loads((repo_root / "examples" / "amr-demo" / "machine-ir-v2.json"
                     ).read_text(encoding="utf-8"))
    v, valid = validate_any(v2)
    assert v == 2 and valid["machine"]["id"] == "amr-demo-01"
    with pytest.raises(IRValidationError):
        validate_any({"schema_version": 99})
    with pytest.raises(IRValidationError):
        validate_any({"schema_version": 1})  # missing machine/control


def test_summarize_v1_and_v2(amr_ir_dict, repo_root):
    v, valid = validate_any(amr_ir_dict)
    s = summarize(v, valid)
    assert s["schema_version"] == 1
    assert s["machine"]["id"] == "amr-demo-01"
    assert s["counts"]["sensors"] > 0 and s["counts"]["scenarios"] == 8
    assert len(s["ir_sha256"]) == 64
    assert "states" not in s  # v1 has no state graph
    v2 = json.loads((repo_root / "examples" / "amr-demo" / "machine-ir-v2.json"
                     ).read_text(encoding="utf-8"))
    v, valid = validate_any(v2)
    s = summarize(v, valid)
    assert s["schema_version"] == 2
    assert s["counts"]["states"] == 3 and s["counts"]["transitions"] == 4
    assert len(s["states"]) == 3 and len(s["transitions"]) == 4


def test_name_and_id_rules():
    assert valid_name("my-robot_01") and valid_name("a")
    assert not valid_name("")
    assert not valid_name("../escape")
    assert not valid_name("a/b")
    assert not valid_name(".hidden")
    assert not valid_name("x" * 65)
    assert valid_project_id("prj-abcdef012345")
    assert not valid_project_id("prj-XYZ")
    assert not valid_project_id("../prj-abcdef012345")
    assert not valid_project_id("prj-abcdef012345-extra")


def test_create_get_roundtrip(store, amr_ir_dict):
    created = store.create("my-bot", amr_ir_dict)
    assert created["head"] == 1 and created["name"] == "my-bot"
    assert valid_project_id(created["pid"])
    got = store.get(created["pid"])
    assert got["ir"]["machine"]["id"] == "amr-demo-01"
    assert got["summary"]["machine"]["id"] == "amr-demo-01"


def test_create_rejects_bad_name_and_invalid_ir(store, amr_ir_dict):
    with pytest.raises(ValueError):
        store.create("../escape", amr_ir_dict)
    with pytest.raises(IRValidationError):
        store.create("ok-name", {"schema_version": 1})


def test_create_rejects_oversize_payload(store):
    with pytest.raises(ValueError, match="too large"):
        store.create("big", {"schema_version": 1, "pad": "x" * 300_000})


def test_unknown_project_raises(store, amr_ir_dict):
    with pytest.raises(ProjectNotFound):
        store.get("prj-000000000000")
    with pytest.raises(ProjectNotFound):
        store.get("not-an-id")
    with pytest.raises(ProjectNotFound):
        store.save_revision("prj-000000000000", amr_ir_dict)


def test_save_revision_bumps_head(store, amr_ir_dict):
    pid = store.create("bot", amr_ir_dict)["pid"]
    changed = json.loads(json.dumps(amr_ir_dict))
    changed["control"]["max_linear_speed_mps"] = 0.9
    saved = store.save_revision(pid, changed)
    assert saved == {"pid": pid, "head": 2, "unchanged": False,
                     "summary": saved["summary"]}
    assert store.get(pid)["head"] == 2
    rev1 = store.revision(pid, 1)
    assert rev1["ir"]["control"]["max_linear_speed_mps"] != 0.9


def test_save_identical_is_noop(store, amr_ir_dict):
    pid = store.create("bot", amr_ir_dict)["pid"]
    saved = store.save_revision(pid, json.loads(json.dumps(amr_ir_dict)))
    assert saved["unchanged"] is True and saved["head"] == 1
    assert len(store.history(pid)) == 1


def test_save_invalid_keeps_head(store, amr_ir_dict):
    pid = store.create("bot", amr_ir_dict)["pid"]
    with pytest.raises(IRValidationError):
        store.save_revision(pid, {"schema_version": 1})
    assert store.get(pid)["head"] == 1


def test_history_full_diff_and_export(store, amr_ir_dict):
    pid = store.create("bot", amr_ir_dict)["pid"]
    changed = json.loads(json.dumps(amr_ir_dict))
    changed["control"]["max_linear_speed_mps"] = 0.9
    store.save_revision(pid, changed)
    hist = store.history(pid)
    assert [h["rev"] for h in hist] == [1, 2]
    assert hist[0]["ir_sha256"] != hist[1]["ir_sha256"]
    assert hist[0]["machine"] == hist[1]["machine"] == "amr-demo-01"
    diff = store.diff(pid, 1, 2)
    assert diff["from"] == 1 and diff["to"] == 2 and not diff["truncated"]
    paths = {c["path"] for c in diff["changed"]}
    assert "control.max_linear_speed_mps" in paths
    bundle = store.export(pid)
    assert bundle["project"]["pid"] == pid and bundle["project"]["head"] == 2
    assert bundle["ir"]["control"]["max_linear_speed_mps"] == 0.9
    with pytest.raises(ProjectNotFound):
        store.revision(pid, 3)
    with pytest.raises(ProjectNotFound):
        store.diff(pid, 1, 3)


def test_duplicate_copies_head(store, amr_ir_dict):
    pid = store.create("bot", amr_ir_dict)["pid"]
    dup = store.duplicate(pid, "bot-copy")
    assert dup["pid"] != pid and dup["head"] == 1
    assert store.get(dup["pid"])["ir"] == store.get(pid)["ir"]
    with pytest.raises(ProjectNotFound):
        store.duplicate("prj-000000000000", "ghost")


def test_list_skips_junk(store, amr_ir_dict):
    assert store.list() == []
    pid = store.create("bot", amr_ir_dict)["pid"]
    (store.root / "not-a-project").mkdir()
    (store.root / "prj-ffffffffffff").mkdir()  # no meta.json: ignored
    listed = store.list()
    assert [p["pid"] for p in listed] == [pid]
    assert listed[0]["machine"] == "amr-demo-01"


def test_revision_cap_is_honest(store, amr_ir_dict, monkeypatch):
    import genesis_rt.projects as proj

    monkeypatch.setattr(proj, "MAX_REVISIONS", 2)
    pid = store.create("bot", amr_ir_dict)["pid"]
    changed = json.loads(json.dumps(amr_ir_dict))
    changed["control"]["max_linear_speed_mps"] = 0.9
    store.save_revision(pid, changed)
    changed["control"]["max_linear_speed_mps"] = 0.8
    with pytest.raises(ProjectFull):
        store.save_revision(pid, changed)
    assert store.get(pid)["head"] == 2


def test_ir_diff_kinds_and_paths():
    a = {"x": 1, "gone": True, "nested": {"k": [1, 2]}, "same": "s"}
    b = {"x": 2, "new": 1, "nested": {"k": [1, 3]}, "same": "s"}
    out = ir_diff(a, b)
    assert not out["truncated"]
    by_path = {c["path"]: c for c in out["changed"]}
    assert by_path["x"]["kind"] == "changed"
    assert by_path["gone"]["kind"] == "removed"
    assert by_path["new"]["kind"] == "added"
    assert by_path["nested.k[1]"]["kind"] == "changed"
    assert "same" not in by_path
    # key order alone is not a change
    assert ir_diff({"a": 1, "b": 2}, {"b": 2, "a": 1})["changed"] == []
    # list length change is reported once, then elements pairwise
    out = ir_diff({"l": [1, 2, 3]}, {"l": [1, 9]})
    assert {c["path"] for c in out["changed"]} == {"l", "l[1]"}


def test_ir_diff_truncates_huge_gaps():
    a = {f"k{i}": i for i in range(500)}
    out = ir_diff(a, {})
    assert out["truncated"] is True
    assert len(out["changed"]) == 200
    big = {"v": "y" * 1000}
    (entry,) = ir_diff({"v": "x"}, big)["changed"]
    assert entry["after"].endswith("…(truncated)")
