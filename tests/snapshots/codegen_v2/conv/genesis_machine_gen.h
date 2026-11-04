/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * GENERATED FILE -- DO NOT EDIT.
 * machine: conveyor-demo-01 (conveyor)
 * generator: 0.1.0, machine templates: 2.0
 * ir_sha256: c938068d4cc9a60cc5718100232c4415f07732f40e5eb03b81035d313d969e90
 *
 * Machine-specific queries derived from Machine IR v2: state machine,
 * command contracts, fault responses, actuator bounds, sensor models,
 * telemetry map. Fail-closed: unknown ids return -1/0/NULL, never data.
 */
#ifndef GENESIS_MACHINE_GEN_H
#define GENESIS_MACHINE_GEN_H

typedef enum {
    GENESIS_M_STATE_INIT = 0,
    GENESIS_M_STATE_RUNNING = 1,
    GENESIS_M_STATE_SAFE_STOP = 2,
    GENESIS_M_STATE_COUNT = 3
} genesis_m_state_t;

typedef enum {
    GENESIS_M_EVENT_START = 0,
    GENESIS_M_EVENT_ESTOP = 1,
    GENESIS_M_EVENT_FAULT_DETECTED = 2,
    GENESIS_M_EVENT_RESET = 3,
    GENESIS_M_EVENT_COUNT = 4
} genesis_m_event_t;

typedef enum {
    GENESIS_M_CMD_BELT_CMD = 0,
    GENESIS_M_CMD_COUNT = 1
} genesis_m_cmd_t;

typedef enum {
    GENESIS_M_FAULT_COMMAND_REJECTED = 0,
    GENESIS_M_FAULT_SIMULATOR_DISCONNECT = 1,
    GENESIS_M_FAULT_COUNT = 2
} genesis_m_fault_t;

typedef enum {
    GENESIS_M_ACTION_REJECT_COMMAND = 0,
    GENESIS_M_ACTION_COMMAND_VIRTUAL_STOP = 1,
    GENESIS_M_ACTION_COUNT = 2
} genesis_m_action_t;

typedef enum {
    GENESIS_M_ACT_BELT = 0,
    GENESIS_M_ACT_COUNT = 1
} genesis_m_act_t;

typedef enum {
    GENESIS_M_SENS_BELT_SPEED = 0,
    GENESIS_M_SENS_ESTOP = 1,
    GENESIS_M_SENS_COUNT = 2
} genesis_m_sens_t;

typedef enum {
    GENESIS_M_TM_BELT_SPEED_TM = 0,
    GENESIS_M_TM_ESTOP_TM = 1,
    GENESIS_M_TM_COUNT = 2
} genesis_m_tm_t;

/* 1 when (from_state -> to_state on event) is a declared transition. */
int genesis_machine_can_transition(int from_state, int to_state, int event);

/* Number of contract fields for a command, or -1 when unknown. */
int genesis_machine_cmd_field_count(int cmd);

/* Bounds of command field <field>; 0 on success, -1 when unknown. */
int genesis_machine_cmd_field_bounds(int cmd, int field,
                                     double *min_out, double *max_out);

/* Safe state + action for a fault; first IR entry wins. 0/-1. */
int genesis_machine_fault_response(int fault, int *state_out, int *action_out);

/* Actuator command bounds. 0 on success, -1 when unknown. */
int genesis_machine_actuator_bounds(int actuator,
                                    double *min_out, double *max_out);

/* Sensor freshness limit in ms. 0 on success, -1 when unknown. */
int genesis_machine_sensor_freshness(int sensor, double *ms_out);

/* Sensor declared range; -1 when the sensor declares no range. */
int genesis_machine_sensor_range(int sensor, double *min_out, double *max_out);

/* Telemetry entries by index (0..GENESIS_M_TM_COUNT-1). */
int genesis_machine_telemetry_rate(int tm, double *rate_out);
const char *genesis_machine_telemetry_name(int tm);
const char *genesis_machine_telemetry_source(int tm);

#endif /* GENESIS_MACHINE_GEN_H */
