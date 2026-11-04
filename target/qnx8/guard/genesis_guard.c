/* Copyright 2026 GENESIS RT contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * genesis_guard: policy-enforcing command server.
 * QNX: named channel, MsgReceive/MsgReply loop, monotonic clock checks.
 * Host (non-QNX): informative stub; policy logic is tested through
 * target/qnx8/host_tests/guard_vector instead.
 */
#include <stdio.h>
#include <string.h>
#include "genesis_ipc.h"
#include "guard_policy.h"

#ifdef __QNXNTO__
#include <errno.h>
#include <sys/dispatch.h>
#include <sys/neutrino.h>

static genesis_limits_t g_limits = {1.2, 1.0, 100};
static genesis_guard_ctx_t g_ctx = {0, GENESIS_ST_NOMINAL, 0};

int main(int argc, char **argv) {
    (void)argc;
    (void)argv;
    name_attach_t *attach = name_attach(NULL, GENESIS_ATTACH_NAME, 0);
    if (attach == NULL) {
        fprintf(stderr, "guard: name_attach failed: %s\n", strerror(errno));
        return 1;
    }
    printf("guard: attached as '%s' chid=%d\n", GENESIS_ATTACH_NAME, attach->chid);
    fflush(stdout);
    for (;;) {
        genesis_cmd_t cmd;
        memset(&cmd, 0, sizeof cmd);
        int rcvid = MsgReceive(attach->chid, &cmd, sizeof cmd, NULL);
        if (rcvid < 0) {
            fprintf(stderr, "guard: MsgReceive failed: %s\n", strerror(errno));
            continue;
        }
        if (rcvid == 0) {
            /* Pulse: acknowledge, never treat as a command. */
            MsgReply(rcvid, EOK, NULL, 0);
            continue;
        }
        genesis_verdict_t v =
            genesis_guard_decide(&cmd, (uint32_t)sizeof cmd, &g_ctx, &g_limits);
        g_ctx.state = v.state_out;
        genesis_reply_t reply;
        reply.decision = v.decision;
        reply.reason = v.reason;
        reply.state_out = v.state_out;
        MsgReply(rcvid, EOK, &reply, sizeof reply);
        printf("guard: seq=%u decision=%s reason=%s state=%u\n", cmd.seq,
               v.decision == GENESIS_ALLOW ? "ALLOW" : "DENY",
               genesis_reason_str(v.reason), v.state_out);
        fflush(stdout);
    }
    /* unreachable */
    return 0;
}
#else
int main(void) {
    printf("genesis_guard host stub: native QNX IPC transport requires QNX Neutrino.\n"
           "Policy logic is verified on host via guard_vector; see host_tests/.\n");
    return 2;
}
#endif
