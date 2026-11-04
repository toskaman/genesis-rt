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
/* Machine-specific limits BAKED IN at build time from the generated
 * header (`genesis-rt generate` output, `-I.` on the compile line).
 * A missing/stale header is a compile error, never a silent default:
 * the guard cannot run with limits from another machine. */
#include "genesis_config_gen.h"

static genesis_limits_t g_limits = {GENESIS_MAX_LINEAR_MPS,
                                    GENESIS_MAX_ANGULAR_RADPS,
                                    GENESIS_FRESHNESS_LIMIT_MS};
static genesis_guard_ctx_t g_ctx = {0, GENESIS_ST_NOMINAL, 0};
static uint64_t g_allows = 0;
static uint64_t g_denies = 0;
static uint32_t g_last_reason = GENESIS_R_OK;
static uint32_t g_ndropped = 0;

int main(int argc, char **argv) {
    (void)argc;
    (void)argv;
    name_attach_t *attach = name_attach(NULL, GENESIS_ATTACH_NAME, 0);
    if (attach == NULL) {
        fprintf(stderr, "guard: name_attach failed: %s\n", strerror(errno));
        return 1;
    }
    printf("guard: attached as '%s' chid=%d\n", GENESIS_ATTACH_NAME, attach->chid);
    printf("guard: machine=%s limits linear=%.3f angular=%.3f freshness=%ums\n",
           GENESIS_MACHINE_ID, g_limits.max_linear_speed_mps,
           g_limits.max_angular_speed_radps, g_limits.freshness_limit_ms);
    fflush(stdout);
    for (;;) {
        union {
            genesis_cmd_t cmd;
            genesis_stats_req_t stats;
            unsigned char raw[64];
        } msg;
        struct _msg_info info;
        memset(&msg, 0, sizeof msg);
        memset(&info, 0, sizeof info);
        int rcvid = MsgReceive(attach->chid, &msg, sizeof msg, &info);
        if (rcvid < 0) {
            fprintf(stderr, "guard: MsgReceive failed: %s\n", strerror(errno));
            continue;
        }
        if (rcvid == 0) {
            /* Pulse: never reply, never treat as a command. */
            continue;
        }
        /* The policy sees the SENDER's byte count, never our buffer size:
         * short or overlong frames must hit BAD_SIZE. */
        uint32_t nbytes = (uint32_t)info.msglen;
        if (nbytes == (uint32_t)sizeof(msg.stats) &&
            msg.stats.magic == GENESIS_STATS_MAGIC &&
            msg.stats.version == GENESIS_STATS_VERSION) {
            genesis_stats_reply_t s;
            s.state = g_ctx.state;
            s.last_reason = g_last_reason;
            s.last_seq = g_ctx.last_seq;
            s.ndropped = g_ndropped;
            s.allows = g_allows;
            s.denies = g_denies;
            MsgReply(rcvid, EOK, &s, sizeof s);
            continue;
        }
        genesis_verdict_t v =
            genesis_guard_decide(&msg.cmd, nbytes, &g_ctx, &g_limits);
        g_ctx.state = v.state_out;
        if (v.decision == GENESIS_ALLOW) {
            g_allows++;
        } else {
            g_denies++;
            g_last_reason = v.reason;
            if (v.reason == GENESIS_R_BAD_MAGIC || v.reason == GENESIS_R_BAD_VERSION ||
                v.reason == GENESIS_R_BAD_SIZE || v.reason == GENESIS_R_MALFORMED)
                g_ndropped++;
        }
        genesis_reply_t reply;
        reply.decision = v.decision;
        reply.reason = v.reason;
        reply.state_out = v.state_out;
        MsgReply(rcvid, EOK, &reply, sizeof reply);
        printf("guard: seq=%u decision=%s reason=%s state=%u\n", msg.cmd.seq,
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
