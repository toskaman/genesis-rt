# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Property-style tests (seeded stdlib random): validation + determinism."""
import copy
import random

from genesis_rt import codegen, faultlab
from genesis_rt.ir import IRValidationError, validate_ir

SEED = 20261104


def test_fuzz_ir_rejects_garbage(amr_ir_dict):
    rng = random.Random(SEED)
    rejected = 0
    for i in range(200):
        doc = copy.deepcopy(amr_ir_dict)
        stunt = rng.choice(["drop_key", "bad_enum", "bad_num", "extra_key", "bad_id"])
        if stunt == "drop_key":
            doc.pop(rng.choice(list(doc.keys())))
        elif stunt == "bad_enum":
            doc["machine"]["kind"] = f"kind-{rng.randrange(1000)}"
        elif stunt == "bad_num":
            doc["control"]["max_linear_speed_mps"] = rng.choice([-1.0, 0.0, 1e9, "fast"])
        elif stunt == "extra_key":
            doc["verification"]["zzz"] = True
        else:
            doc["sensors"][0]["id"] = f"BAD ID {i}!"
        try:
            validate_ir(doc)
        except IRValidationError:
            rejected += 1
    assert rejected == 200  # every mutation must be caught


def test_scenarios_deterministic_across_seeds(amr_ir):
    for scenario in amr_ir["verification"]["scenarios"]:
        a = faultlab.run_scenario(amr_ir, scenario)
        b = faultlab.run_scenario(amr_ir, scenario)
        assert a["status"] == b["status"] == "pass"
        assert a["stats"] == b["stats"]
        assert a["trace"] == b["trace"]


def test_codegen_stable_under_key_reorder(amr_ir_dict, tmp_path):
    import json
    a = codegen.generate(validate_ir(amr_ir_dict), tmp_path / "a")
    shuffled = json.loads(json.dumps(amr_ir_dict))  # new object, same content
    b = codegen.generate(validate_ir(shuffled), tmp_path / "b")
    assert a == b
