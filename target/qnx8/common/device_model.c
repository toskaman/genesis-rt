/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 */
#include "device_model.h"

void genesis_device_state_init(genesis_device_state_t *s) {
    s->x = 0.0;
    s->y = 0.0;
    s->theta = 0.0;
    s->v = 0.0;
    s->w = 0.0;
    s->last_apply_ms = 0;
    s->applied = 0;
    s->last_seq = 0;
}

int genesis_device_apply(genesis_device_state_t *s, double linear_mps,
                         double angular_radps, uint32_t seq, uint64_t now_ms) {
    if (s->applied > 0 && seq <= s->last_seq)
        return 0; /* stale or duplicate: never integrate twice */
    double dt = 0.0;
    if (s->applied > 0 && now_ms > s->last_apply_ms) {
        dt = (double)(now_ms - s->last_apply_ms) / 1000.0;
        if (dt > 1.0)
            dt = 1.0; /* clamp: a wedged sender must not teleport the pose */
    }
    /* Integrate with the PREVIOUS setpoint over dt, then latch the new one:
     * velocity applies from the moment it arrives, not retroactively. */
    s->x += s->v * dt;
    s->theta += s->w * dt;
    s->v = linear_mps;
    s->w = angular_radps;
    s->last_apply_ms = now_ms;
    s->last_seq = seq;
    s->applied++;
    return 1;
}

void genesis_device_watchdog(genesis_device_state_t *s, uint64_t now_ms) {
    if (s->applied > 0 && now_ms >= s->last_apply_ms &&
        now_ms - s->last_apply_ms > GENESIS_DEVICE_WATCHDOG_MS) {
        s->v = 0.0;
        s->w = 0.0;
    }
}
