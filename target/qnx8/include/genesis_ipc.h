/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * GENESIS RT native IPC protocol (QNX Neutrino message passing).
 * Fixed-size frames, explicit versioning, monotonic sequence IDs.
 */
#ifndef GENESIS_IPC_H
#define GENESIS_IPC_H

#include <stdint.h>

#define GENESIS_PROTOCOL_MAGIC 0x47454E31u /* "GEN1" */
#define GENESIS_PROTOCOL_VERSION 1u
#define GENESIS_ATTACH_NAME "genesis_guard"

/* Guard states */
#define GENESIS_ST_INIT 0
#define GENESIS_ST_NOMINAL 1
#define GENESIS_ST_DEGRADED 2
#define GENESIS_ST_SAFE_STOP 3

/* Decisions */
#define GENESIS_ALLOW 0
#define GENESIS_DENY 1

/* Deny reasons */
typedef enum {
    GENESIS_R_OK = 0,
    GENESIS_R_BAD_MAGIC = 1,
    GENESIS_R_BAD_VERSION = 2,
    GENESIS_R_BAD_SIZE = 3,
    GENESIS_R_STALE_SEQ = 4,
    GENESIS_R_OVERDUE_DEADLINE = 5,
    GENESIS_R_STALE_SENSOR = 6,
    GENESIS_R_SIM_DISCONNECTED = 7,
    GENESIS_R_SPEED_OVER_LIMIT = 8,
    GENESIS_R_ANGULAR_OVER_LIMIT = 9,
    GENESIS_R_BAD_TRANSITION = 10,
    GENESIS_R_MALFORMED = 11
} genesis_reason_t;

/* Command frame: controller -> guard. Packed, fixed 40 bytes. */
#pragma pack(push, 1)
typedef struct {
    uint32_t magic;
    uint16_t version;
    uint16_t req_state;
    uint32_t seq;
    uint32_t now_ms;
    uint32_t deadline_ms;
    float linear_mps;
    float angular_radps;
    uint32_t sensor_age_ms;
    uint8_t sim_connected;
    uint8_t reserved[3];
} genesis_cmd_t;

/* Reply frame: guard -> controller. Fixed 12 bytes. */
typedef struct {
    uint32_t decision;
    uint32_t reason;
    uint32_t state_out;
} genesis_reply_t;
#pragma pack(pop)

#endif /* GENESIS_IPC_H */
