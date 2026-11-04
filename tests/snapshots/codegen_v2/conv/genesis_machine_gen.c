/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * GENERATED FILE -- DO NOT EDIT.
 * machine: conveyor-demo-01 (conveyor)
 * generator: 0.1.0, machine templates: 2.0
 * ir_sha256: bf95264e0edf39863b492a75d242e672cbce13db7dddd645f8e9a31535dcec45
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
        return (to_state == GENESIS_M_STATE_SAFE_STOP && event == GENESIS_M_EVENT_ESTOP) ||
               (to_state == GENESIS_M_STATE_SAFE_STOP && event == GENESIS_M_EVENT_FAULT_DETECTED);
    case GENESIS_M_STATE_SAFE_STOP:
        return (to_state == GENESIS_M_STATE_INIT && event == GENESIS_M_EVENT_RESET);
    default:
        return 0;
    }
}

int genesis_machine_cmd_field_count(int cmd) {
    switch (cmd) {
    case GENESIS_M_CMD_BELT_CMD:
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
    case GENESIS_M_CMD_BELT_CMD:
        switch (field) {
        case 0: *min_out = -2.0; *max_out = 2.0; return 0;
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
    case GENESIS_M_ACT_BELT: *min_out = -2.0; *max_out = 2.0; return 0;
    default:
        return -1;
    }
}

int genesis_machine_sensor_freshness(int sensor, double *ms_out) {
    if (ms_out == NULL)
        return -1;
    switch (sensor) {
    case GENESIS_M_SENS_BELT_SPEED: *ms_out = 200.0; return 0;
    case GENESIS_M_SENS_ESTOP: *ms_out = 50.0; return 0;
    default:
        return -1;
    }
}

int genesis_machine_sensor_range(int sensor, double *min_out, double *max_out) {
    if (min_out == NULL || max_out == NULL)
        return -1;
    switch (sensor) {
    case GENESIS_M_SENS_BELT_SPEED: return -1;
    case GENESIS_M_SENS_ESTOP: return -1;
    default:
        return -1;
    }
}

int genesis_machine_telemetry_rate(int tm, double *rate_out) {
    if (rate_out == NULL)
        return -1;
    switch (tm) {
    case GENESIS_M_TM_BELT_SPEED_TM: *rate_out = 5.0; return 0;
    case GENESIS_M_TM_ESTOP_TM: *rate_out = 20.0; return 0;
    default:
        return -1;
    }
}

const char *genesis_machine_telemetry_name(int tm) {
    switch (tm) {
    case GENESIS_M_TM_BELT_SPEED_TM: return "belt-speed-tm";
    case GENESIS_M_TM_ESTOP_TM: return "estop-tm";
    default:
        return NULL;
    }
}

const char *genesis_machine_telemetry_source(int tm) {
    switch (tm) {
    case GENESIS_M_TM_BELT_SPEED_TM: return "belt-speed";
    case GENESIS_M_TM_ESTOP_TM: return "estop";
    default:
        return NULL;
    }
}
