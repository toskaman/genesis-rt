/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Host vector harness: feeds decision vectors through the shared guard
 * policy so Python tests can prove C/Python conformance without QNX.
 *
 * Input line: magic version size_ok seq now_ms deadline_ms linear angular
 *             req_state sensor_age_ms sim_connected reset_armed state_in
 * Output line: DECISION REASON STATE_OUT  (e.g. "DENY SPEED_OVER_LIMIT 1")
 */
#include <stdint.h>
#include <stdio.h>
#include "guard_policy.h"
#include "genesis_ipc.h"

int main(void) {
    /* Defaults match the AMR demo IR; overridden per line below. */
    genesis_limits_t limits = {1.2, 1.0, 100};
    unsigned magic, version, size_ok, seq, now_ms, deadline_ms;
    unsigned req_state, sensor_age, sim_connected, reset_armed, state_in;
    int have_limits = 0;
    int seq_override = 0;
    unsigned seq_base = 0;
    double linear, angular;
    char line[512];

    while (fgets(line, sizeof line, stdin) != NULL) {
        if (line[0] == '#' || line[0] == '\n')
            continue;
        if (!have_limits) {
            if (sscanf(line, "LIMITS %lf %lf %u", &limits.max_linear_speed_mps,
                       &limits.max_angular_speed_radps, &limits.freshness_limit_ms) == 3) {
                have_limits = 1;
                continue;
            }
            have_limits = 1; /* no LIMITS line: keep defaults, parse as vector */
        }
        if (line[0] == 'S' && line[1] == 'E' && line[2] == 'Q' && line[3] == ' ') {
            /* "SEQ <last_seq>": override last_seq for the next vector. */
            if (sscanf(line + 4, "%u", &seq_base) == 1) {
                seq_override = 1;
                printf("SEQ-ARMED %u\n", seq_base);
            } else {
                printf("DENY MALFORMED 3\n");
            }
            fflush(stdout);
            continue;
        }
        if (sscanf(line, "%x %u %u %u %u %u %lf %lf %u %u %u %u %u", &magic, &version,
                   &size_ok, &seq, &now_ms, &deadline_ms, &linear, &angular,
                   &req_state, &sensor_age, &sim_connected, &reset_armed,
                   &state_in) != 13) {
            printf("DENY MALFORMED 3\n");
            fflush(stdout);
            continue;
        }
        genesis_cmd_t cmd;
        cmd.magic = (uint32_t)magic;
        cmd.version = (uint16_t)version;
        cmd.req_state = (uint16_t)req_state;
        cmd.seq = seq;
        cmd.now_ms = now_ms;
        cmd.deadline_ms = deadline_ms;
        cmd.linear_mps = (float)linear;
        cmd.angular_radps = (float)angular;
        cmd.sensor_age_ms = sensor_age;
        cmd.sim_connected = (uint8_t)(sim_connected ? 1 : 0);
        cmd.reserved[0] = cmd.reserved[1] = cmd.reserved[2] = 0;
        genesis_guard_ctx_t ctx;
        if (seq_override) {
            ctx.last_seq = seq_base;
            seq_override = 0;
        } else {
            ctx.last_seq = seq > 0 ? seq - 1 : 0;
        }
        ctx.state = state_in;
        ctx.reset_armed = reset_armed ? 1 : 0;
        {
            uint32_t frame = size_ok ? (uint32_t)sizeof(genesis_cmd_t)
                                     : (uint32_t)sizeof(genesis_cmd_t) - 1;
            genesis_verdict_t v = genesis_guard_decide(&cmd, frame, &ctx, &limits);
            printf("%s %s %u\n", v.decision == GENESIS_ALLOW ? "ALLOW" : "DENY",
                   genesis_reason_str(v.reason), v.state_out);
            fflush(stdout);
        }
    }
    return 0;
}
