# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Single source of truth for current-facing claims (Wave 11 §15).

Documentation consistency tests pin the jury/devpost/commercial docs
to these values. Update here AND in the docs with each measured run;
historical reports keep their own dated numbers.
"""
from .provenance import EXPECTED_TARGET_CHECKS, TARGET_PLATFORM

TESTS_WITH_SDK = 1015
TESTS_SDK_FREE_PASSED = 1010
TESTS_SDK_FREE_SKIPS = 5
ADVERSARIAL_TESTS = 24
PLANNING_EVAL_CASES = 28
QCC_VERSION = "12.2.0"

TARGET_MATRIX_CHECKS = len(EXPECTED_TARGET_CHECKS)
TARGET_PLATFORM_CLAIM = TARGET_PLATFORM
