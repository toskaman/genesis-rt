/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * GENERATED FILE -- DO NOT EDIT.
 * machine: amr-demo-01 (differential_drive_robot)
 * generator: 0.1.0, machine templates: 2.1
 * ir_sha256: 5639d986d258062fcad450260723a04d9de2b4c5432ddef516e81bffefdbe70f
 */
#include "genesis_machine_gen.h"
#include <stddef.h>

int genesis_machine_can_transition(int from_state, int to_state, int event) {
    (void)to_state;
    (void)event;
    switch (from_state) {
    case GENESIS_M_STATE_INIT:
        return (to_state == GENESIS_M_STATE_RUNNING && event == GENESIS_M_EVENT_START);
    case GENESIS_M_STATE_RUNNING:
        return (to_state == GENESIS_M_STATE_SAFE_STOP && event == GENESIS_M_EVENT_FAULT_DETECTED) ||
               (to_state == GENESIS_M_STATE_SAFE_STOP && event == GENESIS_M_EVENT_ESTOP);
    case GENESIS_M_STATE_SAFE_STOP:
        return (to_state == GENESIS_M_STATE_INIT && event == GENESIS_M_EVENT_RESET);
    default:
        return 0;
    }
}

int genesis_machine_wire_of(int v2_state) {
    switch (v2_state) {
    case GENESIS_M_STATE_INIT: return 0;
    case GENESIS_M_STATE_RUNNING: return 1;
    case GENESIS_M_STATE_SAFE_STOP: return 3;
    default:
        return -1;
    }
}

int genesis_machine_cmd_field_count(int cmd) {
    switch (cmd) {
    case GENESIS_M_CMD_LEFT_MOTOR_CMD:
        return 1;
    case GENESIS_M_CMD_RIGHT_MOTOR_CMD:
        return 1;
    default:
        return -1;
    }
}

int genesis_machine_cmd_field_bounds(int cmd, int field,
                                     double *min_out, double *max_out) {
    if (min_out == NULL || max_out == NULL)
        return -1;
    (void)field;
    switch (cmd) {
    case GENESIS_M_CMD_LEFT_MOTOR_CMD:
        switch (field) {
        case 0: *min_out = -1.2; *max_out = 1.2; return 0;
        default: return -1;
        }
    case GENESIS_M_CMD_RIGHT_MOTOR_CMD:
        switch (field) {
        case 0: *min_out = -1.2; *max_out = 1.2; return 0;
        default: return -1;
        }
    default:
        return -1;
    }
}

int genesis_machine_fault_response(int fault, int *state_out, int *action_out) {
    if (state_out == NULL || action_out == NULL)
        return -1;
    switch (fault) {
    case GENESIS_M_FAULT_STALE_SENSOR: *state_out = GENESIS_M_STATE_SAFE_STOP; *action_out = GENESIS_M_ACTION_COMMAND_VIRTUAL_STOP; return 0;
    case GENESIS_M_FAULT_COMMAND_REJECTED: *state_out = GENESIS_M_STATE_SAFE_STOP; *action_out = GENESIS_M_ACTION_REJECT_COMMAND; return 0;
    case GENESIS_M_FAULT_SIMULATOR_DISCONNECT: *state_out = GENESIS_M_STATE_SAFE_STOP; *action_out = GENESIS_M_ACTION_COMMAND_VIRTUAL_STOP; return 0;
    default:
        return -1;
    }
}

int genesis_machine_actuator_bounds(int actuator,
                                    double *min_out, double *max_out) {
    if (min_out == NULL || max_out == NULL)
        return -1;
    switch (actuator) {
    case GENESIS_M_ACT_LEFT_MOTOR: *min_out = -1.2; *max_out = 1.2; return 0;
    case GENESIS_M_ACT_RIGHT_MOTOR: *min_out = -1.2; *max_out = 1.2; return 0;
    default:
        return -1;
    }
}

int genesis_machine_sensor_freshness(int sensor, double *ms_out) {
    if (ms_out == NULL)
        return -1;
    switch (sensor) {
    case GENESIS_M_SENS_PROXIMITY: *ms_out = 100.0; return 0;
    case GENESIS_M_SENS_ODOMETRY: *ms_out = 100.0; return 0;
    default:
        return -1;
    }
}

int genesis_machine_sensor_range(int sensor, double *min_out, double *max_out) {
    if (min_out == NULL || max_out == NULL)
        return -1;
    switch (sensor) {
    case GENESIS_M_SENS_PROXIMITY: *min_out = 0.0; *max_out = 10.0; return 0;
    case GENESIS_M_SENS_ODOMETRY: return -1;
    default:
        return -1;
    }
}

int genesis_machine_telemetry_rate(int tm, double *rate_out) {
    if (rate_out == NULL)
        return -1;
    switch (tm) {
    case GENESIS_M_TM_PROXIMITY_TM: *rate_out = 10.0; return 0;
    case GENESIS_M_TM_ODOMETRY_TM: *rate_out = 100.0; return 0;
    default:
        return -1;
    }
}

const char *genesis_machine_telemetry_name(int tm) {
    switch (tm) {
    case GENESIS_M_TM_PROXIMITY_TM: return "proximity-tm";
    case GENESIS_M_TM_ODOMETRY_TM: return "odometry-tm";
    default:
        return NULL;
    }
}

const char *genesis_machine_telemetry_source(int tm) {
    switch (tm) {
    case GENESIS_M_TM_PROXIMITY_TM: return "proximity";
    case GENESIS_M_TM_ODOMETRY_TM: return "odometry";
    default:
        return NULL;
    }
}
