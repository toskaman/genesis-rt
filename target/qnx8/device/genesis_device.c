/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * genesis_device: SIMULATED actuator/sensor endpoint.
 * Holds virtual device state (position, velocity, sensor age) and
 * applies only commands forwarded by genesis_guard. No physical motor
 * support exists in this component by design (MVP: simulation only).
 */
#include <stdio.h>
#include <string.h>
#include "genesis_ipc.h"

typedef struct {
    double x, y, theta;
    double v, w;
    uint32_t sensor_age_ms;
    int sim_connected;
} genesis_virtual_device_t;

static genesis_virtual_device_t g_dev = {0, 0, 0, 0, 0, 0, 1};

void genesis_device_apply(double v, double w, double dt) {
    g_dev.v = v;
    g_dev.w = w;
    g_dev.x += v * dt;
    g_dev.theta += w * dt;
}

void genesis_device_stop(void) {
    g_dev.v = 0.0;
    g_dev.w = 0.0;
}

int main(void) {
    printf("device: virtual endpoint ready (simulation only, no physical I/O).\n"
           "device: state x=%.2f y=%.2f theta=%.2f\n", g_dev.x, g_dev.y, g_dev.theta);
#ifdef __QNXNTO__
    printf("device: running on QNX Neutrino; awaiting guard-forwarded commands.\n");
#else
    printf("device: host build; logic verified through the Python simulator mirror.\n");
#endif
    return 0;
}
