/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Shared guard policy: pure decision function used by the QNX guard
 * server AND the host test harness. Behavioral mirror of
 * host/genesis_rt/guard_policy.py; both are checked against the same
 * decision vectors (target/qnx8/host_tests/guard_vector.c).
 */
#ifndef GENESIS_GUARD_POLICY_H
#define GENESIS_GUARD_POLICY_H

#include <stdint.h>
#include "genesis_ipc.h"

typedef struct {
    double max_linear_speed_mps;
    double max_angular_speed_radps;
    uint32_t freshness_limit_ms;
} genesis_limits_t;

typedef struct {
    uint32_t last_seq;
    uint32_t state;
    int reset_armed; /* set only via the supervisor path */
} genesis_guard_ctx_t;

typedef struct {
    uint32_t decision; /* GENESIS_ALLOW / GENESIS_DENY */
    uint32_t reason;   /* genesis_reason_t */
    uint32_t state_out;
    int applied;
} genesis_verdict_t;

genesis_verdict_t genesis_guard_decide(const genesis_cmd_t *cmd, uint32_t frame_bytes,
                                       genesis_guard_ctx_t *ctx,
                                       const genesis_limits_t *limits);

const char *genesis_reason_str(uint32_t reason);

#endif /* GENESIS_GUARD_POLICY_H */
