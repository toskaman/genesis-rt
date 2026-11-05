/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Shared guard policy implementation. Order of checks MUST match
 * host/genesis_rt/guard_policy.py exactly:
 * magic -> version -> size -> seq -> deadline -> sensor -> sim link ->
 * estop -> speed -> angular -> state transition. Fail-closed throughout.
 * estop_engaged is strict 0/1: any other byte value is MALFORMED.
 *
 * Sequence freshness uses serial-number arithmetic (RFC 1982): with
 * uint32 seq, delta = seq - last_seq (unsigned wraparound) is accepted
 * iff 1 <= delta < 2^31. Counter wraparound is accepted; duplicates,
 * replays and huge forward jumps are denied STALE_SEQ.
 *
 * Deadline comparison uses the same serial arithmetic (§16): overdue
 * iff 0 < now_ms - deadline_ms (unsigned wraparound) < 2^31. now ==
 * deadline is not overdue. Pairs 2^31+ ms apart are ambiguous by
 * construction and read as "deadline in the future" — unreachable
 * for real near-term deadlines (period + 20ms margin).
 */
#include "guard_policy.h"
#include <math.h>
#include <stddef.h>

#ifdef GENESIS_MACHINE_V2
/* Machine-specific tables, generated from this build's IR v2 by
 * `genesis-rt generate` (templates 2.1+). Only translation units
 * compiled with -DGENESIS_MACHINE_V2 (the v2 guard rule) see them;
 * every other binary keeps the fixed v1 tail below. */
#include "genesis_machine_gen.h"
#endif

static genesis_verdict_t deny(genesis_guard_ctx_t *ctx, uint32_t reason, int latch) {
    genesis_verdict_t v;
    v.decision = GENESIS_DENY;
    v.reason = reason;
    v.state_out = latch ? GENESIS_ST_SAFE_STOP : ctx->state;
    v.applied = 0;
    return v;
}

#ifdef GENESIS_MACHINE_V2
/* 1 when the IR declares <fault> with action reject_command: the fault
 * denies this command but does not latch (the next command is judged
 * on its own; a still-faulty sensor denies again). Any other action,
 * or an undeclared fault, keeps the v1 latch behavior. */
static int v2_fault_is_stateless(int fault) {
    int st = -1, act = -1;
    if (genesis_machine_fault_response(fault, &st, &act) != 0)
        return 0;
    (void)st;
#ifdef GENESIS_M_HAS_ACTION_REJECT_COMMAND
    return act == GENESIS_M_ACTION_REJECT_COMMAND;
#else
    (void)act;
    return 0;
#endif
}

/* 1 when the IR declares fault command_rejected with a stop action:
 * over-limit commands then latch safe-stop instead of denying
 * statelessly (fail-closed direction: the IR may only make a deny
 * stickier, never weaker, for this class). */
static int v2_rejection_demands_stop(void) {
#ifdef GENESIS_M_HAS_FAULT_COMMAND_REJECTED
    int st = -1, act = -1;
    if (genesis_machine_fault_response(GENESIS_M_FAULT_COMMAND_REJECTED,
                                       &st, &act) != 0)
        return 0;
    (void)st;
#ifdef GENESIS_M_HAS_ACTION_COMMAND_VIRTUAL_STOP
    if (act == GENESIS_M_ACTION_COMMAND_VIRTUAL_STOP)
        return 1;
#endif
#ifdef GENESIS_M_HAS_ACTION_ENTER_SAFE_STATE
    if (act == GENESIS_M_ACTION_ENTER_SAFE_STATE)
        return 1;
#endif
    (void)act;
#endif
    return 0;
}

static int v2_latch_stale_sensor(void) {
#ifdef GENESIS_M_HAS_FAULT_STALE_SENSOR
    return !v2_fault_is_stateless(GENESIS_M_FAULT_STALE_SENSOR);
#else
    return 1;
#endif
}

static int v2_latch_sim_disconnected(void) {
#ifdef GENESIS_M_HAS_FAULT_SIMULATOR_DISCONNECT
    return !v2_fault_is_stateless(GENESIS_M_FAULT_SIMULATOR_DISCONNECT);
#else
    return 1;
#endif
}

/* Allow iff some (v2_from, v2_to) interpretation of the wire pair has a
 * declared transition on SOME event. Wire commands carry no event, so
 * any-event is the only sound reading; unmapped wire numbers deny.
 * Integrity-class checks above already ran: this answers only "may the
 * automaton move", never "is the frame trustworthy". */
static int v2_transition_declared(uint32_t wire_from, uint32_t wire_to) {
    int s1, s2, ev;
    if (wire_from > 3 || wire_to > 3)
        return 0;
    for (s1 = 0; s1 < GENESIS_M_STATE_COUNT; s1++) {
        if (genesis_machine_wire_of(s1) != (int)wire_from)
            continue;
        for (s2 = 0; s2 < GENESIS_M_STATE_COUNT; s2++) {
            if (genesis_machine_wire_of(s2) != (int)wire_to)
                continue;
            for (ev = 0; ev < GENESIS_M_EVENT_COUNT; ev++) {
                if (genesis_machine_can_transition(s1, s2, ev))
                    return 1;
            }
        }
    }
    return 0;
}
#else
static int v2_latch_stale_sensor(void) { return 1; }
static int v2_latch_sim_disconnected(void) { return 1; }
static int v2_rejection_demands_stop(void) { return 0; }
#endif

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
    {
        uint32_t overdue = cmd->now_ms - cmd->deadline_ms; /* wraps mod 2^32 */
        if (overdue != 0 && overdue < 0x80000000u)
            return deny(ctx, GENESIS_R_OVERDUE_DEADLINE, 0);
    }
    if (cmd->sensor_age_ms > limits->freshness_limit_ms)
        return deny(ctx, GENESIS_R_STALE_SENSOR, v2_latch_stale_sensor());
    if (!cmd->sim_connected)
        return deny(ctx, GENESIS_R_SIM_DISCONNECTED, v2_latch_sim_disconnected());
    if (cmd->estop_engaged > 1)
        return deny(ctx, GENESIS_R_MALFORMED, 1);
    if (cmd->estop_engaged)
        return deny(ctx, GENESIS_R_ESTOP, 1);
    if (fabs((double)cmd->linear_mps) > limits->max_linear_speed_mps)
        return deny(ctx, GENESIS_R_SPEED_OVER_LIMIT, v2_rejection_demands_stop());
    if (fabs((double)cmd->angular_radps) > limits->max_angular_speed_radps)
        return deny(ctx, GENESIS_R_ANGULAR_OVER_LIMIT, v2_rejection_demands_stop());

#ifdef GENESIS_MACHINE_V2
    /* v2 tail: leaving wire SAFE_STOP still needs the supervisor reset;
     * otherwise the generated transition table decides. A command that
     * requests the current state is not a transition (self-loops are
     * unrepresentable: the IR validator rejects self transitions). */
    if (ctx->state == GENESIS_ST_SAFE_STOP && !ctx->reset_armed)
        return deny(ctx, GENESIS_R_BAD_TRANSITION, 1);
    if (cmd->req_state != ctx->state &&
        !v2_transition_declared(ctx->state, cmd->req_state))
        return deny(ctx, GENESIS_R_BAD_TRANSITION,
                    ctx->state == GENESIS_ST_SAFE_STOP ? 1 : 0);
    ctx->last_seq = cmd->seq;
    ctx->reset_armed = 0;
    v.decision = GENESIS_ALLOW;
    v.reason = GENESIS_R_OK;
    v.state_out = cmd->req_state;
    v.applied = 1;
    return v;
#else
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
#endif
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
    case GENESIS_R_ESTOP: return "ESTOP";
    default: return "MALFORMED";
    }
}
