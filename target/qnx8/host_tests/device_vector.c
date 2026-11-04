/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Host vector harness for the pure device kinematics model.
 *
 * Input lines:
 *   APPLY <linear> <angular> <seq> <now_ms>   -> integrate one command
 *   TICK <now_ms>                           -> run watchdog only
 *   BELT_APPLY <v> <seq> <now_ms>            -> belt integrate
 *   BELT_JAM <0|1>                           -> belt jam input
 *   BELT_TICK <now_ms>                       -> belt watchdog only
 * Output line: APPLIED=<0|1> X=<f> THETA=<f> V=<f> W=<f> N=<applied> SEQ=<last>
 * Belt output: APPLIED=<0|1> POS=<f> SPEED=<f> JAMMED=<0|1> N=<applied> SEQ=<last>
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "device_model.h"

int main(void) {
    genesis_device_state_t dev;
    genesis_device_state_init(&dev);
    genesis_belt_state_t belt;
    genesis_belt_state_init(&belt);
    char line[256];
    while (fgets(line, sizeof line, stdin) != NULL) {
        if (line[0] == '#' || line[0] == '\n')
            continue;
        if (strncmp(line, "APPLY ", 6) == 0) {
            double v, w;
            unsigned seq;
            unsigned long long now;
            if (sscanf(line + 6, "%lf %lf %u %llu", &v, &w, &seq, &now) != 4) {
                printf("BADLINE\n");
                fflush(stdout);
                continue;
            }
            int ok = genesis_device_apply(&dev, v, w, seq, (uint64_t)now);
            printf("APPLIED=%d X=%.6f THETA=%.6f V=%.6f W=%.6f N=%llu SEQ=%u\n",
                   ok, dev.x, dev.theta, dev.v, dev.w,
                   (unsigned long long)dev.applied, dev.last_seq);
        } else if (strncmp(line, "TICK ", 5) == 0) {
            unsigned long long now;
            if (sscanf(line + 5, "%llu", &now) != 1) {
                printf("BADLINE\n");
                fflush(stdout);
                continue;
            }
            genesis_device_watchdog(&dev, (uint64_t)now);
            printf("APPLIED=- X=%.6f THETA=%.6f V=%.6f W=%.6f N=%llu SEQ=%u\n",
                   dev.x, dev.theta, dev.v, dev.w,
                   (unsigned long long)dev.applied, dev.last_seq);
        } else if (strncmp(line, "BELT_APPLY ", 11) == 0) {
            double v;
            unsigned seq;
            unsigned long long now;
            if (sscanf(line + 11, "%lf %u %llu", &v, &seq, &now) != 3) {
                printf("BADLINE\n");
                fflush(stdout);
                continue;
            }
            int ok = genesis_belt_apply(&belt, v, seq, (uint64_t)now);
            printf("APPLIED=%d POS=%.6f SPEED=%.6f JAMMED=%d N=%llu SEQ=%u\n",
                   ok, belt.position_m, belt.speed_mps, belt.jammed,
                   (unsigned long long)belt.applied, belt.last_seq);
        } else if (strncmp(line, "BELT_JAM ", 9) == 0) {
            int jam = 0;
            if (sscanf(line + 9, "%d", &jam) != 1 || (jam != 0 && jam != 1)) {
                printf("BADLINE\n");
                fflush(stdout);
                continue;
            }
            genesis_belt_set_jam(&belt, jam);
            printf("APPLIED=- POS=%.6f SPEED=%.6f JAMMED=%d N=%llu SEQ=%u\n",
                   belt.position_m, belt.speed_mps, belt.jammed,
                   (unsigned long long)belt.applied, belt.last_seq);
        } else if (strncmp(line, "BELT_TICK ", 10) == 0) {
            unsigned long long now;
            if (sscanf(line + 10, "%llu", &now) != 1) {
                printf("BADLINE\n");
                fflush(stdout);
                continue;
            }
            genesis_belt_watchdog(&belt, (uint64_t)now);
            printf("APPLIED=- POS=%.6f SPEED=%.6f JAMMED=%d N=%llu SEQ=%u\n",
                   belt.position_m, belt.speed_mps, belt.jammed,
                   (unsigned long long)belt.applied, belt.last_seq);
        } else {
            printf("BADLINE\n");
        }
        fflush(stdout);
    }
    return 0;
}
