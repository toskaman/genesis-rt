/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * GENERATED FILE -- DO NOT EDIT.
 * machine: amr-demo-01 (differential_drive_robot)
 * generator: 0.1.0, machine templates: 2.0
 * ir_sha256: 5639d986d258062fcad450260723a04d9de2b4c5432ddef516e81bffefdbe70f
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
    GENESIS_M_EVENT_FAULT_DETECTED = 1,
    GENESIS_M_EVENT_ESTOP = 2,
    GENESIS_M_EVENT_RESET = 3,
    GENESIS_M_EVENT_COUNT = 4
} genesis_m_event_t;

typedef enum {
    GENESIS_M_CMD_LEFT_MOTOR_CMD = 0,
    GENESIS_M_CMD_RIGHT_MOTOR_CMD = 1,
    GENESIS_M_CMD_COUNT = 2
} genesis_m_cmd_t;

typedef enum {
    GENESIS_M_FAULT_STALE_SENSOR = 0,
    GENESIS_M_FAULT_COMMAND_REJECTED = 1,
    GENESIS_M_FAULT_SIMULATOR_DISCONNECT = 2,
    GENESIS_M_FAULT_COUNT = 3
} genesis_m_fault_t;

typedef enum {
    GENESIS_M_ACTION_COMMAND_VIRTUAL_STOP = 0,
    GENESIS_M_ACTION_REJECT_COMMAND = 1,
    GENESIS_M_ACTION_COUNT = 2
} genesis_m_action_t;

typedef enum {
    GENESIS_M_ACT_LEFT_MOTOR = 0,
    GENESIS_M_ACT_RIGHT_MOTOR = 1,
    GENESIS_M_ACT_COUNT = 2
} genesis_m_act_t;

typedef enum {
    GENESIS_M_SENS_PROXIMITY = 0,
    GENESIS_M_SENS_ODOMETRY = 1,
    GENESIS_M_SENS_COUNT = 2
} genesis_m_sens_t;

typedef enum {
    GENESIS_M_TM_PROXIMITY_TM = 0,
    GENESIS_M_TM_ODOMETRY_TM = 1,
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
