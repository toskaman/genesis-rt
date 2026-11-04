/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Pure virtual-device kinematics shared by the QNX device server and the
 * host test harness. No QNX headers, no I/O: identical behavior on both.
 */
#ifndef GENESIS_DEVICE_MODEL_H
#define GENESIS_DEVICE_MODEL_H

#include <stdint.h>

#define GENESIS_DEVICE_WATCHDOG_MS 500u

typedef struct {
    double x, y, theta;      /* integrated pose (virtual meters/radians) */
    double v, w;             /* last applied velocity setpoint */
    uint64_t last_apply_ms;  /* target monotonic clock of last apply */
    uint64_t applied;        /* validated commands applied since start */
    uint32_t last_seq;       /* guard sequence of last applied command */
} genesis_device_state_t;

void genesis_device_state_init(genesis_device_state_t *s);

/* Integrate one validated command. dt comes from the TARGET monotonic
 * clock (arrival times), never from sender timestamps. First command
 * applies with dt=0 (stamps pose, no motion yet). Out-of-order seq
 * (seq <= last_seq with applied > 0) is ignored and reported as 0,
 * applied as 1. */
int genesis_device_apply(genesis_device_state_t *s, double linear_mps,
                         double angular_radps, uint32_t seq, uint64_t now_ms);

/* Actuator watchdog: zero the velocity setpoint when no validated
 * command arrived within GENESIS_DEVICE_WATCHDOG_MS. Pose is kept. */
void genesis_device_watchdog(genesis_device_state_t *s, uint64_t now_ms);

/* Belt variant: 1D position/speed with a jam input. Same conventions
 * as the pose model (arrival-dt, previous setpoint, dt clamp 1 s,
 * stale-seq ignore, 500 ms watchdog). While jammed, apply decays the
 * speed (*=0.5 per command, snapped to 0 below 1e-12) and the position
 * never advances. */
typedef struct {
    double position_m;
    double speed_mps;
    int jammed;
    uint64_t last_apply_ms;
    uint64_t applied;
    uint32_t last_seq;
} genesis_belt_state_t;

void genesis_belt_state_init(genesis_belt_state_t *s);
int genesis_belt_apply(genesis_belt_state_t *s, double belt_mps,
                       uint32_t seq, uint64_t now_ms);
void genesis_belt_set_jam(genesis_belt_state_t *s, int jammed);
void genesis_belt_watchdog(genesis_belt_state_t *s, uint64_t now_ms);

#endif /* GENESIS_DEVICE_MODEL_H */
