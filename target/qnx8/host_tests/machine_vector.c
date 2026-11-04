/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Host vector harness for the generated machine module: feeds queries
 * through genesis_machine_gen.c so Python tests can prove the GENERATED
 * logic matches the IR it was derived from (no QNX needed).
 *
 * Input lines (integer ids are IR-order ordinals):
 *   T <from> <to> <event>   -> "1" or "0"
 *   C <cmd> <field>         -> "<min> <max>" or "ERR"
 *   F <fault>               -> "<state> <action>" or "ERR"
 *   A <actuator>            -> "<min> <max>" or "ERR"
 *   S <sensor>              -> "<fresh_ms> <rmin> <rmax>" ("NONE" x2 if no range) or "ERR"
 *   M <tm>                  -> "<rate> <name> <source>" or "ERR"
 *   W <v2state>            -> "<wire 0..3>" or "ERR"
 */
#include <stdio.h>
#include "genesis_machine_gen.h"

int main(void) {
    char line[256];
    setvbuf(stdout, NULL, _IONBF, 0);
    while (fgets(line, sizeof line, stdin) != NULL) {
        if (line[0] == '#' || line[0] == '\n')
            continue;
        if (line[0] == 'T') {
            int from, to, ev;
            if (sscanf(line + 1, "%d %d %d", &from, &to, &ev) != 3) {
                printf("ERR\n");
                continue;
            }
            printf("%d\n", genesis_machine_can_transition(from, to, ev));
        } else if (line[0] == 'C') {
            int cmd, field;
            double lo, hi;
            if (sscanf(line + 1, "%d %d", &cmd, &field) != 2) {
                printf("ERR\n");
                continue;
            }
            if (genesis_machine_cmd_field_bounds(cmd, field, &lo, &hi) == 0)
                printf("%.17g %.17g\n", lo, hi);
            else
                printf("ERR\n");
        } else if (line[0] == 'F') {
            int fault, state, action;
            if (sscanf(line + 1, "%d", &fault) != 1) {
                printf("ERR\n");
                continue;
            }
            if (genesis_machine_fault_response(fault, &state, &action) == 0)
                printf("%d %d\n", state, action);
            else
                printf("ERR\n");
        } else if (line[0] == 'A') {
            int act;
            double lo, hi;
            if (sscanf(line + 1, "%d", &act) != 1) {
                printf("ERR\n");
                continue;
            }
            if (genesis_machine_actuator_bounds(act, &lo, &hi) == 0)
                printf("%.17g %.17g\n", lo, hi);
            else
                printf("ERR\n");
        } else if (line[0] == 'S') {
            int sens;
            double fresh, rlo, rhi;
            if (sscanf(line + 1, "%d", &sens) != 1) {
                printf("ERR\n");
                continue;
            }
            if (genesis_machine_sensor_freshness(sens, &fresh) != 0) {
                printf("ERR\n");
                continue;
            }
            if (genesis_machine_sensor_range(sens, &rlo, &rhi) == 0)
                printf("%.17g %.17g %.17g\n", fresh, rlo, rhi);
            else
                printf("%.17g NONE NONE\n", fresh);
        } else if (line[0] == 'M') {
            int tm;
            double rate;
            const char *name, *src;
            if (sscanf(line + 1, "%d", &tm) != 1) {
                printf("ERR\n");
                continue;
            }
            name = genesis_machine_telemetry_name(tm);
            src = genesis_machine_telemetry_source(tm);
            if (genesis_machine_telemetry_rate(tm, &rate) != 0
                || name == NULL || src == NULL) {
                printf("ERR\n");
                continue;
            }
            printf("%.17g %s %s\n", rate, name, src);
        } else if (line[0] == 'W') {
            int st, wire;
            if (sscanf(line + 1, "%d", &st) != 1) {
                printf("ERR\n");
                continue;
            }
            wire = genesis_machine_wire_of(st);
            if (wire < 0)
                printf("ERR\n");
            else
                printf("%d\n", wire);
        } else {
            printf("ERR\n");
        }
    }
    return 0;
}
