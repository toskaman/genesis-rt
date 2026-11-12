# Copyright 2026 GENESIS RT contributors
# SPDX-License-Identifier: Apache-2.0
"""Single source of truth for current-facing claims (Wave 11 §15).

Documentation consistency tests pin the jury/devpost/commercial docs
to these values. Update here AND in the docs with each measured run;
historical reports keep their own dated numbers.
"""
from .provenance import EXPECTED_TARGET_CHECKS, TARGET_PLATFORM

# TESTS_WITH_SDK is the collected total. Skips are environment-dependent,
# never zero by assumption: SDK-only tests skip without the SDK, and the
# 2 axe-core scans skip without node_modules/axe-core. Guarded by
# test_total_count_matches_collected.
TESTS_WITH_SDK = 1611
TESTS_SDK_FREE_PASSED = 1605
TESTS_MEASURED_ON = "2026-11-10 TITAN OMEGA7+wow+causal+video (SDK + axe, Windows, Python 3.14; SDK-free lane via probe-reported absent SDK)"
TESTS_SDK_FREE_SKIPS = 6
ADVERSARIAL_TESTS = 24
PLANNING_EVAL_CASES = 28
QCC_VERSION = "12.2.0"
E2E_BROWSER_TESTS = 44
# No video file is shipped: all cuts were withdrawn on 2026-11-12 for an
# owner remake (see docs/demo-video-plan.md). Historical durations/hashes
# stay in docs/demo/MEDIA_VALIDATION_*.md as dated records, never as pins.
VIDEO_WITHDRAWN = "2026-11-12"
PACK_BEFORE = "evidence/qnx8-x86_64-omega2-before"
PACK_AFTER = "evidence/qnx8-x86_64-omega2-after"

TARGET_MATRIX_CHECKS = len(EXPECTED_TARGET_CHECKS)
TARGET_PLATFORM_CLAIM = TARGET_PLATFORM
