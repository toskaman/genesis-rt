/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * genesis_faultinject: on-target guard verification client.
 * Sends a fixed sequence of nominal and faulty commands to genesis_guard
 * over native message passing and checks each reply against the expected
 * verdict. Order matters: non-latching denials first, latching BAD_MAGIC
 * last, then proof that SAFE_STOP holds. Exit 0 only if all match.
 */
#include <stdio.h>
#include <string.h>
#include "genesis_ipc.h"

#ifdef __QNXNTO__
#include <sys/dispatch.h>
#include <sys/neutrino.h>
#include <time.h>

static uint64_t now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000u + (uint64_t)ts.tv_nsec / 1000000u;
}

static int failures = 0;

static void check(int coid, const char *name, genesis_cmd_t *cmd,
                  uint32_t want_decision, uint32_t want_reason) {
    genesis_reply_t reply;
    memset(&reply, 0, sizeof reply);
    if (MsgSend(coid, cmd, sizeof *cmd, &reply, sizeof reply) < 0) {
        printf("FAIL %-18s MsgSend error\n", name);
        failures++;
        return;
    }
    int ok = (reply.decision == want_decision && reply.reason == want_reason);
    printf("%s %-18s decision=%u reason=%u state=%u (want %u/%u)\n",
           ok ? "PASS" : "FAIL", name, reply.decision, reply.reason,
           reply.state_out, want_decision, want_reason);
    if (!ok)
        failures++;
}

int main(void) {
    int coid = name_open(GENESIS_ATTACH_NAME, 0);
    if (coid < 0) {
        printf("FAIL faultinject: guard not found (start genesis_guard first)\n");
        return 2;
    }
    uint32_t seq = 0;
    genesis_cmd_t cmd;
    uint64_t t;

    /* 1. nominal: must ALLOW */
    memset(&cmd, 0, sizeof cmd);
    cmd.magic = GENESIS_PROTOCOL_MAGIC;
    cmd.version = GENESIS_PROTOCOL_VERSION;
    cmd.req_state = GENESIS_ST_NOMINAL;
    cmd.seq = ++seq;
    t = now_ms();
    cmd.now_ms = (uint32_t)t;
    cmd.deadline_ms = (uint32_t)t + 30u;
    cmd.linear_mps = 0.5f;
    cmd.sensor_age_ms = 0;
    cmd.sim_connected = 1;
    check(coid, "nominal", &cmd, GENESIS_ALLOW, GENESIS_R_OK);

    /* 2. over-limit speed: DENY, no latch */
    cmd.seq = ++seq;
    t = now_ms();
    cmd.now_ms = (uint32_t)t;
    cmd.deadline_ms = (uint32_t)t + 30u;
    cmd.linear_mps = 5.0f;
    check(coid, "over_limit", &cmd, GENESIS_DENY, GENESIS_R_SPEED_OVER_LIMIT);
    cmd.linear_mps = 0.5f;

    /* 3. replayed sequence: DENY. Only ACCEPTED seqs are consumed, so we
     * replay seq 1 (accepted in step 1), not seq 2 (denied in step 2). */
    cmd.seq = 1;
    t = now_ms();
    cmd.now_ms = (uint32_t)t;
    cmd.deadline_ms = (uint32_t)t + 30u;
    check(coid, "replay_seq", &cmd, GENESIS_DENY, GENESIS_R_STALE_SEQ);
    cmd.seq = ++seq;

    /* 4. overdue deadline: DENY */
    t = now_ms();
    cmd.now_ms = (uint32_t)t;
    cmd.deadline_ms = (uint32_t)t - 50u;
    check(coid, "overdue", &cmd, GENESIS_DENY, GENESIS_R_OVERDUE_DEADLINE);
    cmd.seq = ++seq;

    /* 5. corrupted magic: DENY + latch SAFE_STOP */
    t = now_ms();
    cmd.now_ms = (uint32_t)t;
    cmd.deadline_ms = (uint32_t)t + 30u;
    cmd.magic = 0xDEADBEEFu;
    check(coid, "bad_magic", &cmd, GENESIS_DENY, GENESIS_R_BAD_MAGIC);
    cmd.magic = GENESIS_PROTOCOL_MAGIC;
    cmd.seq = ++seq;

    /* 6. nominal after latch: must stay DENIED (safe stop holds) */
    t = now_ms();
    cmd.now_ms = (uint32_t)t;
    cmd.deadline_ms = (uint32_t)t + 30u;
    check(coid, "locked_nominal", &cmd, GENESIS_DENY, GENESIS_R_BAD_TRANSITION);

    printf("faultinject: %s\n", failures == 0 ? "ALL 6 CHECKS PASS" : "FAILURES PRESENT");
    return failures == 0 ? 0 : 1;
}
#else
int main(void) {
    printf("genesis_faultinject host stub: native QNX IPC requires QNX Neutrino.\n");
    return 2;
}
#endif
