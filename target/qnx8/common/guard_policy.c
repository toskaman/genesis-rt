/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Shared guard policy implementation. Order of checks MUST match
 * host/genesis_rt/guard_policy.py exactly:
 * magic -> version -> size -> seq -> deadline -> sensor -> sim link ->
 * speed -> angular -> state transition. Fail-closed throughout.
 *
 * Sequence freshness uses serial-number arithmetic (RFC 1982): with
 * uint32 seq, delta = seq - last_seq (unsigned wraparound) is accepted
 * iff 1 <= delta < 2^31. Counter wraparound is accepted; duplicates,
 * replays and huge forward jumps are denied STALE_SEQ.
 */
#include "guard_policy.h"
#include <math.h>
#include <stddef.h>

static genesis_verdict_t deny(genesis_guard_ctx_t *ctx, uint32_t reason, int latch) {
    genesis_verdict_t v;
    v.decision = GENESIS_DENY;
    v.reason = reason;
    v.state_out = latch ? GENESIS_ST_SAFE_STOP : ctx->state;
    v.applied = 0;
    return v;
}

genesis_verdict_t genesis_guard_decide(const genesis_cmd_t *cmd, uint32_t frame_bytes,
                                       genesis_guard_ctx_t *ctx,
                                       const genesis_limits_t *limits) {
    genesis_verdict_t v;
    if (cmd == NULL || ctx == NULL || limits == NULL) {
        v.decision = GENESIS_DENY;
        v.reason = GENESIS_R_MALFORMED;
        v.state_out = GENESIS_ST_SAFE_STOP;
        v.applied = 0;
        return v;
    }
    if (cmd->magic != GENESIS_PROTOCOL_MAGIC)
        return deny(ctx, GENESIS_R_BAD_MAGIC, 1);
    if (cmd->version != GENESIS_PROTOCOL_VERSION)
        return deny(ctx, GENESIS_R_BAD_VERSION, 1);
    if (frame_bytes != (uint32_t)sizeof(genesis_cmd_t))
        return deny(ctx, GENESIS_R_BAD_SIZE, 1);
    if (isnan(cmd->linear_mps) || isnan(cmd->angular_radps) ||
        isinf(cmd->linear_mps) || isinf(cmd->angular_radps))
        return deny(ctx, GENESIS_R_MALFORMED, 1);
    {
        uint32_t delta = cmd->seq - ctx->last_seq; /* wraps mod 2^32 */
        if (delta == 0 || delta >= 0x80000000u)
            return deny(ctx, GENESIS_R_STALE_SEQ, 0);
    }
    if (cmd->now_ms > cmd->deadline_ms)
        return deny(ctx, GENESIS_R_OVERDUE_DEADLINE, 0);
    if (cmd->sensor_age_ms > limits->freshness_limit_ms)
        return deny(ctx, GENESIS_R_STALE_SENSOR, 1);
    if (!cmd->sim_connected)
        return deny(ctx, GENESIS_R_SIM_DISCONNECTED, 1);
    if (fabs((double)cmd->linear_mps) > limits->max_linear_speed_mps)
        return deny(ctx, GENESIS_R_SPEED_OVER_LIMIT, 0);
    if (fabs((double)cmd->angular_radps) > limits->max_angular_speed_radps)
        return deny(ctx, GENESIS_R_ANGULAR_OVER_LIMIT, 0);

    if (ctx->state == GENESIS_ST_SAFE_STOP) {
        if (!ctx->reset_armed)
            return deny(ctx, GENESIS_R_BAD_TRANSITION, 1);
        if (cmd->req_state != GENESIS_ST_NOMINAL && cmd->req_state != GENESIS_ST_DEGRADED)
            return deny(ctx, GENESIS_R_BAD_TRANSITION, 1);
        ctx->last_seq = cmd->seq;
        ctx->reset_armed = 0;
        v.decision = GENESIS_ALLOW;
        v.reason = GENESIS_R_OK;
        v.state_out = cmd->req_state;
        v.applied = 1;
        return v;
    }
    if (cmd->req_state != GENESIS_ST_NOMINAL && cmd->req_state != GENESIS_ST_DEGRADED)
        return deny(ctx, GENESIS_R_BAD_TRANSITION, 0);
    ctx->last_seq = cmd->seq;
    v.decision = GENESIS_ALLOW;
    v.reason = GENESIS_R_OK;
    v.state_out = cmd->req_state;
    v.applied = 1;
    return v;
}

const char *genesis_reason_str(uint32_t reason) {
    switch (reason) {
    case GENESIS_R_OK: return "OK";
    case GENESIS_R_BAD_MAGIC: return "BAD_MAGIC";
    case GENESIS_R_BAD_VERSION: return "BAD_VERSION";
    case GENESIS_R_BAD_SIZE: return "BAD_SIZE";
    case GENESIS_R_STALE_SEQ: return "STALE_SEQ";
    case GENESIS_R_OVERDUE_DEADLINE: return "OVERDUE_DEADLINE";
    case GENESIS_R_STALE_SENSOR: return "STALE_SENSOR";
    case GENESIS_R_SIM_DISCONNECTED: return "SIM_DISCONNECTED";
    case GENESIS_R_SPEED_OVER_LIMIT: return "SPEED_OVER_LIMIT";
    case GENESIS_R_ANGULAR_OVER_LIMIT: return "ANGULAR_OVER_LIMIT";
    case GENESIS_R_BAD_TRANSITION: return "BAD_TRANSITION";
    default: return "MALFORMED";
    }
}
