/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * genesis_controller: periodic client. Sends actuation requests to
 * genesis_guard via native message passing; NEVER bypasses the guard
 * to reach the virtual device. Applies only ALLOWed commands.
 */
#include <stdio.h>
#include <string.h>
#include "genesis_ipc.h"

#ifdef __QNXNTO__
#include <errno.h>
#include <stdlib.h>
#include <sys/dispatch.h>
#include <sys/neutrino.h>
#include <time.h>
#include <unistd.h>

static uint64_t now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000u + (uint64_t)ts.tv_nsec / 1000000u;
}

int main(int argc, char **argv) {
    int period_ms = 10;
    if (argc > 1)
        period_ms = atoi(argv[1]);
    if (period_ms < 1 || period_ms > 1000) {
        fprintf(stderr, "controller: bad period_ms\n");
        return 1;
    }
    int coid = name_open(GENESIS_ATTACH_NAME, 0);
    if (coid < 0) {
        fprintf(stderr, "controller: name_open failed: %s\n", strerror(errno));
        return 1;
    }
    printf("controller: connected to '%s', period=%dms\n", GENESIS_ATTACH_NAME, period_ms);
    uint32_t seq = 0;
    for (;;) {
        genesis_cmd_t cmd;
        memset(&cmd, 0, sizeof cmd);
        cmd.magic = GENESIS_PROTOCOL_MAGIC;
        cmd.version = GENESIS_PROTOCOL_VERSION;
        cmd.req_state = GENESIS_ST_NOMINAL;
        cmd.seq = ++seq;
        cmd.now_ms = (uint32_t)now_ms();
        cmd.deadline_ms = cmd.now_ms + (uint32_t)period_ms + 20u;
        cmd.linear_mps = 0.5f; /* virtual corridor cruise */
        cmd.angular_radps = 0.0f;
        cmd.sensor_age_ms = 0;
        cmd.sim_connected = 1;
        genesis_reply_t reply;
        memset(&reply, 0, sizeof reply);
        if (MsgSend(coid, &cmd, sizeof cmd, &reply, sizeof reply) < 0) {
            fprintf(stderr, "controller: MsgSend failed: %s\n", strerror(errno));
            return 1;
        }
        printf("controller: seq=%u decision=%s reason=%u state=%u\n", cmd.seq,
               reply.decision == GENESIS_ALLOW ? "ALLOW" : "DENY", reply.reason,
               reply.state_out);
        fflush(stdout);
        usleep((useconds_t)period_ms * 1000u);
    }
    return 0;
}
#else
int main(void) {
    printf("genesis_controller host stub: native QNX IPC requires QNX Neutrino.\n");
    return 2;
}
#endif
