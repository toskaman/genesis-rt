# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Unit tests: numeric canonicalization of validated Machine IR.

A JSON round-trip through a float-unaware producer (JavaScript:
``JSON.parse`` then ``JSON.stringify`` turns ``1.0`` into ``1``) must not
change the digest of a validated IR. Validators therefore canonicalize
every int-or-float field: float-semantic fields are stored as float,
int-semantic fields collapse integral floats to int, and genuinely
fractional values are never truncated.
"""
import copy
import json

import pytest

from genesis_rt.codegen import ir_sha256
from genesis_rt.ir import IRValidationError, validate_ir
from genesis_rt.ir_v2 import IRValidationError as V2Error
from genesis_rt.ir_v2 import validate_v2


def js_damage(value):
    """Emulate a JSON round-trip through JavaScript numbers.

    JS has a single number type and serializes the shortest form, so
    integral floats lose their ``.0``. All corpus integers are far below
    2**53, so no precision loss applies.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {k: js_damage(v) for k, v in value.items()}
    if isinstance(value, list):
        return [js_damage(v) for v in value]
    return value


def _load_example(repo_root, *parts):
    return json.loads((repo_root.joinpath(*parts)).read_text(encoding="utf-8"))


# History locks: canonicalization must not move these digests.
EXAMPLE_DIGESTS = {
    ("examples", "amr-demo", "machine-ir.json"):
        "356dc135f27f4586e1131fe1e43eac0b054dc7f2fb1f1ba7506fd4d5667ce34d",
    ("examples", "conveyor-demo", "machine-ir.json"):
        "abce9deabbfbd4a264e058e04a2e63dcb8bb3c38e48de31d50ef0397309ec6bd",
    ("examples", "cell-demo", "cell-ir.json"):
        "73e52055d0173770bf904470f2fa565d95a198495ea386ad526366976776ff9b",
    ("examples", "amr-demo", "machine-ir-v2.json"):
        "5639d986d258062fcad450260723a04d9de2b4c5432ddef516e81bffefdbe70f",
    ("examples", "conveyor-demo", "machine-ir-v2.json"):
        "b106e4cdbfc6f78b79b1ef0be75fa35d31c845dd8556831a5edb676373945ae1",
}


def _validate(doc):
    if doc.get("schema_version") == 1:
        return validate_ir(doc)
    return validate_v2(doc)


@pytest.mark.parametrize("parts", sorted(EXAMPLE_DIGESTS))
def test_example_digest_stable(repo_root, parts):
    assert ir_sha256(_validate(_load_example(repo_root, *parts))) == EXAMPLE_DIGESTS[parts]


@pytest.mark.parametrize("parts", sorted(EXAMPLE_DIGESTS))
def test_js_round_trip_preserves_digest(repo_root, parts):
    raw = _load_example(repo_root, *parts)
    assert ir_sha256(_validate(js_damage(copy.deepcopy(raw)))) == EXAMPLE_DIGESTS[parts]


def test_v1_int_spelled_speeds_validate_as_float(amr_ir_dict):
    doc = copy.deepcopy(amr_ir_dict)
    doc["control"]["max_angular_speed_radps"] = int(
        doc["control"]["max_angular_speed_radps"])
    norm = validate_ir(doc)
    assert norm["control"]["max_linear_speed_mps"] == 1.2
    assert isinstance(norm["control"]["max_linear_speed_mps"], float)
    assert isinstance(norm["control"]["max_angular_speed_radps"], float)
    assert ir_sha256(norm) == ir_sha256(validate_ir(amr_ir_dict))


def test_v1_int_spelled_station_x_validates_as_float(repo_root):
    raw = _load_example(repo_root, "examples", "cell-demo", "cell-ir.json")
    doc = copy.deepcopy(raw)
    doc["cell"]["station_x_m"] = int(doc["cell"]["station_x_m"])
    norm = validate_ir(doc)
    assert isinstance(norm["cell"]["station_x_m"], float)
    assert ir_sha256(norm) == ir_sha256(validate_ir(raw))


def test_v1_strict_int_fields_still_reject_float(amr_ir_dict):
    doc = copy.deepcopy(amr_ir_dict)
    doc["control"]["period_ms"] = 20.0
    with pytest.raises(IRValidationError):
        validate_ir(doc)


def _amr_v2(repo_root):
    return _load_example(repo_root, "examples", "amr-demo", "machine-ir-v2.json")


def test_v2_int_spelled_bounds_validate_as_float(repo_root):
    raw = _amr_v2(repo_root)
    norm = validate_v2(js_damage(copy.deepcopy(raw)))
    assert isinstance(norm["actuators"][0]["bounds"]["min"], float)
    assert isinstance(norm["actuators"][0]["bounds"]["max"], float)
    assert isinstance(norm["actuators"][0]["rate_limit"], float)
    assert ir_sha256(norm) == ir_sha256(validate_v2(raw))


def test_v2_integral_float_period_validates_as_int(repo_root):
    raw = _amr_v2(repo_root)
    doc = copy.deepcopy(raw)
    doc["control"]["period_ms"] = float(doc["control"]["period_ms"])
    doc["sensors"][0]["freshness_limit_ms"] = float(
        doc["sensors"][0]["freshness_limit_ms"])
    doc["simulation"]["dt_ms"] = float(doc["simulation"]["dt_ms"])
    doc["simulation"]["duration_ms"] = float(doc["simulation"]["duration_ms"])
    norm = validate_v2(doc)
    assert norm["control"]["period_ms"] == raw["control"]["period_ms"]
    assert isinstance(norm["control"]["period_ms"], int)
    assert isinstance(norm["sensors"][0]["freshness_limit_ms"], int)
    assert isinstance(norm["simulation"]["dt_ms"], int)
    assert ir_sha256(norm) == ir_sha256(validate_v2(raw))


def test_v2_fractional_values_never_truncated(repo_root):
    raw = _amr_v2(repo_root)
    doc = copy.deepcopy(raw)
    doc["telemetry"][0]["rate_hz"] = 10.5
    doc["actuators"][0]["bounds"]["max"] = 1.25
    norm = validate_v2(doc)
    assert norm["telemetry"][0]["rate_hz"] == 10.5
    assert norm["actuators"][0]["bounds"]["max"] == 1.25


def test_v2_schema_version_float_canonicalizes_to_int(repo_root):
    raw = _amr_v2(repo_root)
    doc = copy.deepcopy(raw)
    doc["schema_version"] = 2.0
    norm = validate_v2(doc)
    assert norm["schema_version"] == 2
    assert isinstance(norm["schema_version"], int)
    assert ir_sha256(norm) == ir_sha256(validate_v2(raw))


def test_v2_rejects_bool_numbers(repo_root):
    raw = _amr_v2(repo_root)
    doc = copy.deepcopy(raw)
    doc["control"]["period_ms"] = True
    with pytest.raises(V2Error):
        validate_v2(doc)
