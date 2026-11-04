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
/* Default period + cruise speed come from the generated machine header;
 * argv[1] may override the period for tests, but the shipped default is
 * always the compiled-in machine contract. */
#include "genesis_config_gen.h"

static uint64_t now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000u + (uint64_t)ts.tv_nsec / 1000000u;
}

/* One-shot 2 s guard-call timeout, re-armed before every MsgSend so a
 * hung server fails loudly instead of wedging the control loop. */
static int arm_ipc_timeout(void) {
    struct sigevent ev;
    uint64_t to = 2000000000ULL;
    memset(&ev, 0, sizeof ev);
    ev.sigev_notify = SIGEV_UNBLOCK;
    return TimerTimeout(CLOCK_MONOTONIC, _NTO_TIMEOUT_SEND | _NTO_TIMEOUT_REPLY,
                        &ev, &to, NULL);
}

int main(int argc, char **argv) {
    int period_ms = GENESIS_PERIOD_MS;
    if (argc > 1)
        period_ms = atoi(argv[1]);
    if (period_ms < 1 || period_ms > 1000) {
        fprintf(stderr, "controller: bad period_ms\n");
        return 1;
    }
    /* Cruise at 40% of the machine's own limit: nominal on every machine,
     * over-limit on none. Never a magic constant. */
    float cruise_mps = (float)(0.4 * GENESIS_MAX_LINEAR_MPS);
    int coid = name_open(GENESIS_ATTACH_NAME, 0);
    if (coid < 0) {
        fprintf(stderr, "controller: name_open failed: %s\n", strerror(errno));
        return 1;
    }
    printf("controller: machine=%s connected to '%s', period=%dms cruise=%.3f\n",
           GENESIS_MACHINE_ID, GENESIS_ATTACH_NAME, period_ms, cruise_mps);
    /* Drift-free schedule: absolute wake-ups, not usleep() chaining. */
    struct timespec next;
    clock_gettime(CLOCK_MONOTONIC, &next);
    uint32_t seq = 0;
    for (;;) {
        genesis_cmd_t cmd;
        memset(&cmd, 0, sizeof cmd);
        cmd.magic = GENESIS_PROTOCOL_MAGIC;
        cmd.version = GENESIS_PROTOCOL_VERSION;
        cmd.req_state = GENESIS_ST_NOMINAL;
        cmd.seq = ++seq;
        cmd.now_ms = (uint32_t)now_ms();
        /* NOTE: uint32 ms wraps every ~49.7 d; a command straddling the
         * wrap is denied OVERDUE once, then the stream resumes. A 64-bit
         * time design is future work (see docs/limitations-and-safety.md). */
        cmd.deadline_ms = cmd.now_ms + (uint32_t)period_ms + 20u;
        cmd.linear_mps = cruise_mps; /* virtual corridor cruise */
        cmd.angular_radps = 0.0f;
        cmd.sensor_age_ms = 0;
        cmd.sim_connected = 1;
        genesis_reply_t reply;
        /* Fail-closed fill: ALLOW is 0, so a short/empty reply must never
         * look like an approval. MsgSend returns 0/-1 (no byte count). */
        memset(&reply, 0xFF, sizeof reply);
        if (arm_ipc_timeout() != 0) {
            fprintf(stderr, "controller: TimerTimeout failed: %s\n", strerror(errno));
            return 1;
        }
        if (MsgSend(coid, &cmd, sizeof cmd, &reply, sizeof reply) != 0) {
            fprintf(stderr, "controller: MsgSend failed: %s\n", strerror(errno));
            return 1;
        }
        printf("controller: seq=%u decision=%s reason=%u state=%u\n", cmd.seq,
               reply.decision == GENESIS_ALLOW ? "ALLOW" : "DENY", reply.reason,
               reply.state_out);
        fflush(stdout);
        next.tv_nsec += (long)period_ms * 1000000L;
        while (next.tv_nsec >= 1000000000L) {
            next.tv_nsec -= 1000000000L;
            next.tv_sec++;
        }
        if (clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &next, NULL) != 0) {
            fprintf(stderr, "controller: clock_nanosleep failed: %s\n",
                    strerror(errno));
            return 1;
        }
    }
    return 0;
}
#else
int main(void) {
    printf("genesis_controller host stub: native QNX IPC requires QNX Neutrino.\n");
    return 2;
}
#endif
