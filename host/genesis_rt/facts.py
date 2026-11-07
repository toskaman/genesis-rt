# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Single source of truth for current-facing claims (Wave 11 §15).

Documentation consistency tests pin the jury/devpost/commercial docs
to these values. Update here AND in the docs with each measured run;
historical reports keep their own dated numbers.
"""
from .provenance import EXPECTED_TARGET_CHECKS, TARGET_PLATFORM

# TESTS_WITH_SDK is the collected total: with the QNX SDK every test runs
# (0 skips). Guarded by test_total_count_matches_collected.
TESTS_WITH_SDK = 1140
TESTS_SDK_FREE_PASSED = 1135
TESTS_MEASURED_ON = "2026-11-07 (SDK-free, Linux, Python 3.13)"
TESTS_SDK_FREE_SKIPS = 5
ADVERSARIAL_TESTS = 24
PLANNING_EVAL_CASES = 28
QCC_VERSION = "12.2.0"
E2E_BROWSER_TESTS = 21
VIDEO_FILE = "docs/demo/genesis-rt-demo-w12.mp4"
VIDEO_DURATION_S = 154.664
PACK_BEFORE = "evidence/qnx8-x86_64-w11-before"
PACK_AFTER = "evidence/qnx8-x86_64-w11-after"

TARGET_MATRIX_CHECKS = len(EXPECTED_TARGET_CHECKS)
TARGET_PLATFORM_CLAIM = TARGET_PLATFORM
