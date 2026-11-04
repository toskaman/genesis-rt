/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Host vector harness for the pure device kinematics model.
 *
 * Input lines:
 *   APPLY <linear> <angular> <seq> <now_ms>   -> integrate one command
 *   TICK <now_ms>                           -> run watchdog only
 * Output line: APPLIED=<0|1> X=<f> THETA=<f> V=<f> W=<f> N=<applied> SEQ=<last>
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "device_model.h"

int main(void) {
    genesis_device_state_t dev;
    genesis_device_state_init(&dev);
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
        } else {
            printf("BADLINE\n");
        }
        fflush(stdout);
    }
    return 0;
}
